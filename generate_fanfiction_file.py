import os
from requests import get
from requests.exceptions import RequestException
from contextlib import closing
from bs4 import BeautifulSoup, Tag, NavigableString
from typing import List, Dict, Optional, Any
from collections import OrderedDict
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.fonts import addMapping
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing, Line
import sys
sys.setrecursionlimit(3000)

# Download web pages to get the raw HTML, with the help of the requests package
def simple_get(url:str):
    """
    Attempts to get the content at 'url' by making an HTTP GET request.
    If the content-type of response is some kind of HTML/XML, return the text content, otherwise return None.
    """
    try:
        #The closing() function ensures that any network resources are freed when they go out of scope in the with block.
        #Using closing() is a good practice to help prevent fatal errors and network timeouts
        with closing(get(url, stream=True)) as resp:
            if is_good_response(resp):
                print("HTTP Error: {0}".format(resp.raise_for_status()))
                print(resp.headers)
                #the content is the HTML document
                return resp.content
            else:
                return None

    except RequestException as e:
        log_error('Error during requests to {0} : {1}'.format(url, str(e)))
        return None


def is_good_response(resp)-> bool:
    """
     Return True if the response seems to be HTML, otherwise return False.
    """
    content_type = resp.headers['Content-Type'].lower()
    print("HTTP Status Code: {0}".format(resp.status_code))
    return (resp.status_code == 200 and content_type is not None and content_type.find('html') > -1)


def log_error(e):
    """
    This function prints the errors.
    """
    print(e)


def get_num_of_chapters(url: str) -> int:
    """
    Return the total number of chapters in the fanfic.

    :param url: The URL of a fanfic at any chapter.
    :return: The total number of chapters in the fanfic.
    """

    response = simple_get(url)

    if response is not None:
        html = BeautifulSoup(response, 'html.parser')
        option_tags = html.find("select")
        if option_tags is not None: #multi-chapter situation
            values = [o.get('value') for o in option_tags.find_all("option")] # AttributeError: 'NoneType' object has no attribute 'find_all'; create a check for html.find("select") first. What does find() return?
            return int(values[-1])
        else: #one-chapter situation
            return 1
    else:
        #Raise an exception if we failed to get any data from the url
        raise Exception('Error retrieving contents at {}'.format(url))

def slice_link(url: str) -> str:
    """
    Return a modified link of the fanfic to be scraped. Modified to insert chapter values into the fanfic link.
    :param url: The URL of a fanfic at any chapter.
    """
    first_slice = url.rsplit('/', 1)  # first would print something like ['https://www.fanfiction.net/s/8559914/1', 'Fledgling']
    second_slice = first_slice[0].rsplit('/', 1) # second would print something like ['https://www.fanfiction.net/s/8559914', '1']
    id_ = second_slice[0]
    title = first_slice[1]
    chap = '/{}/'
    link = id_ + chap + title
    return link

def generate_links(url: str) -> List:
    """
    Return a list of links to all chapters of a fanfic, in chronological order.
    :param url: The URL of a fanfic at any chapter.
    """
    num_chaps = get_num_of_chapters(url)
    if num_chaps == 1:
        return [url]
    else:
        link = slice_link(url)
        lst = []
        for n in range(1, num_chaps + 1):
            lst.append(link.format(n)) #string format method
        return lst


def get_title(url: str) -> str:
    """
    Get the title of the fanfiction, without any non-alphnumeric characters between words.
    """
    first_slice = url.rsplit('/', 1)
    title = first_slice[1]
    normal_title = title.replace('-', ' ')
    return normal_title

def get_chap_name(url: str) -> List:
    """
    Get a list of all the chapter names/titles of the fanfiction.
    :param url:
    :return:
    """
    response = simple_get(url)

    if response is not None:
        html = BeautifulSoup(response, 'html.parser')
        option_tags = html.find("select", attrs={"id": "chap_select"})
        if option_tags is not None: # multi-chapter situation
            for option in option_tags:
                text = option.get_text('|||') # ||| as a unique marker to later split by
                lst_chap_names = text.split('|||')
                return lst_chap_names
        else: # one-chapter situation
            return []
    else:
        # Raise an exception if we failed to get any data from the url
        raise Exception('Error retrieving contents at {}'.format(url))


#Select and extract from the raw HTML using BeautifulSoup, to get text
# The BeautifulSoup constructor parses raw HTML strings and produces an object that mirrors the HTML document's structure
# The object includes a lot of methods to select, view, and manipulatethe DOM nodes and text content
#Extract the textual content of a chapter:

def get_text_r_helper(line: BeautifulSoup) -> Any:
        if isinstance(line, Tag) and line.name == 'p' or line.name == 'em' or line.name == 'strong':
            stringify_replace = str(line).replace('<span style="text-decoration:underline;">', "<u>"). \
                replace('<span style="text-decoration: underline;">', "<u>").replace("</span>", "</u>"). \
                replace("\xa0", "").replace("<p></p>", "").replace('<br/>', "")
            return stringify_replace
        elif isinstance(line, NavigableString):
            stringify_replace = str(line).replace("\xa0", "").replace('\n', "").strip()
            return stringify_replace
        else: # any other tag 
            lst_text = []
            for l in line:
                temp = get_text_r_helper(l)
                if isinstance(temp, list):
                    lst_text.extend(temp)
                else:
                    lst_text.append(temp)
            return lst_text


def get_text_r(url: str) -> List:
    lst_text = []
    response = simple_get(url)
    if response is not None:
        html = BeautifulSoup(response, 'lxml')
        story = html.find("div", attrs={"id": "storytext"})
        if story is None:
            story = html.find("div", attrs={"id": "storycontext"})
        for line in story:
            temp = get_text_r_helper(line)
            if isinstance(temp, list):
                lst_text.extend(temp)
            else:
                lst_text.append(temp)
    else:
        #Raise an exception if we failed to get any data from the url
        raise Exception('Error retrieving contents at {}'.format(url))
    lst_text = list(filter(None, lst_text))
    return lst_text


# def get_text(url: str)-> List:
#     """
#     Downloads the fanfiction page and returns a list of all the paragraphs in a chapter.
#     """
#     lst_text = []
#     response = simple_get(url)
#     if response is not None:
#         html = BeautifulSoup(response, 'lxml')
#         story = html.find("div", attrs={"id": "storytext"})
#         if story is None:
#             story = html.find("div", attrs={"id": "storycontent"})
#
#         for line in story:
#             if line.name == 'p':
#                 stringify_replace = str(line).replace('<span style="text-decoration:underline;">', "<u>").\
#                     replace('<span style="text-decoration: underline;">', "<u>").replace("</span>", "</u>").\
#                     replace("\xa0", "")
#                 lst_text.append(stringify_replace)
#             elif line.name == 'div':
#                 for child in line.descendants:
#                     if child.name == 'p':
#                         stringify_replace = str(child).replace('<span style="text-decoration:underline;">', "<u>"). \
#                             replace('<span style="text-decoration: underline;">', "<u>").replace("</span>", "</u>"). \
#                             replace("\xa0", "")
#                         lst_text.append(stringify_replace)
#             else:
#                 if str(line) != '\n':
#                     stringify_replace = str(line).replace('<br/>', "").replace("\xa0", "").strip()
#                     lst_text.append(stringify_replace)
#     else:
#         #Raise an exception if we failed to get any data from the url
#         raise Exception('Error retrieving contents at {}'.format(url))
#
#     lst_text = list(filter(None, lst_text))
#     return lst_text


def get_profile(url: str) -> Dict:
    """
    Return a dictionary containing the fanfiction's profile information
    i.e. title, author, publication date, number of chapters, total words,
    fandom, characters, genre, rating, updated date, summary,  ...

    :param url: The URL of a fanfic at any chapter.
    """

    response = simple_get(url)

    if response is not None:
        html = BeautifulSoup(response, 'html.parser')
        profile = html.find(id="profile_top")

        # Getting the values for the dictionary
        # Main values
        title = profile.find("b").get_text()
        author = profile.find("a").get_text()
        author_link = "https://www.fanfiction.net/" + profile.find("a").get('href')
        summary = profile.find("div", attrs={"class": "xcontrast_txt"}).get_text()
        fandom = html.find("span", attrs={"class": "lc-left"}).find_all("a")[-1].get_text()
        # Stats
        rating = profile.find("span", attrs={"class": "xgray"}).find("a").get_text()
        lst_dates = profile.find("span", attrs={"class": "xgray"}).find_all("span")
        # Someimtes there are is an updated date, sometimes there isn't one
        if len(lst_dates) != 1:
            updated_date = lst_dates[0].get_text()
            publication_date = lst_dates[1].get_text()
        else:
            publication_date = lst_dates[0].get_text()
            updated_date = '' # empty string '' evaluates to False (is falsy, but not equal to False)

        # a string containing rating, genre, characters, words, status, and more ...
        stats = profile.find("span", attrs={"class": "xgray"}).get_text()
        # print(stats)
        stats_split = stats.split(" - ")
        # print(stats_split)
        for i in range(len(stats_split)):
            stats_split[i] = stats_split[i].lstrip()

        # check for existence of certain profile keys i.e. genre, characters, chapters, and status
        genres = ['Adventure', 'Angst', 'Crime', 'Drama', 'Family', 'Fantasy', 'Friendship', 'General', 'Horror',
                  'Humor',
                  'Hurt/Comfort', 'Mystery', 'Parody', 'Poetry', 'Romance', 'Sci-Fi', 'Spiritual', 'Supernatural',
                  'Suspense',
                  'Tragedy', 'Western']

        # Checking to see if the fanfic is one-chapter or more
        option_tags = html.find("select")
        if option_tags is not None:  # multi-chapter fic; profile key 'Chapters' exist
            if stats_split[2].split("/")[0] in genres:
                genre = stats_split[2]
                if "Chapters:" in stats_split[3]:
                    characters = ''
                    chapters = stats_split[3].split(":")[1].strip()
                    words_split = stats_split[4].split(":")
                else:
                    characters = stats_split[3]
                    chapters = stats_split[4].split(":")[1].strip()
                    words_split = stats_split[5].split(":")
            else: # genre doesn't exist
                if "Chapters:" in stats_split[2]:
                    characters = ''
                    chapters = stats_split[2].split(":")[1].strip()
                    words_split = stats_split[3].split(":")
                else:
                    characters = stats_split[2]
                    chapters = stats_split[3].split(":")[1].strip()
                    words_split = stats_split[4].split(":")
                genre = ''
        else: # single chapter fic; "Chapters' profile key DNE
            chapters = "1"
            if stats_split[2].split("/")[0] in genres:
                genre = stats_split[2]
                if "Words:" in stats_split[3]:
                    characters = ''
                    words_split = stats_split[3].split(":")
                else:
                    characters = stats_split[3]
                    words_split = stats_split[4].split(":")
            else:
                if "Words:" in stats_split[2]:
                    characters = ''
                    words_split = stats_split[2].split(":")
                else:
                    characters = stats_split[2]
                    words_split = stats_split[3].split(":")
                genre = ''
        words = words_split[1]

        if "Status: Complete" in stats_split:
            status = "Complete"
        else:
            status = "In-Progress"

        # Create dictionary
        profile_dict = {'title': title,
                        'author': author,
                        'summary': summary,
                        'fandom': fandom,
                        'rating': rating,
                        'updated_date': updated_date,
                        'publication_date': publication_date,
                        'genre': genre,
                        'characters': characters,
                        'chapters': chapters,
                        'words': words,
                        'status': status,
                        'author_link': author_link
                        }
        # print(profile_dict)
        return profile_dict

    else:
        #Raise an exception if we failed to get any data from the url
        raise Exception('Error retrieving contents at {}'.format(url))


def get_path(filename: str) -> str:
    """
    Return a string that is the path to the fanfiction folder,
    ending in the pdf file to be created.
    :param filename: The file name.
    """
    dirname = "fanfiction"
    path = os.path.join(dirname, filename)
    return path


def register_fonts() -> None:
    """
    Register the desired font to be used in the PDF.
    """
    pdfmetrics.registerFont(TTFont('Georgia', 'fonts\Georgia Regular font.ttf'))
    pdfmetrics.registerFont(TTFont('Georgia Italic', 'fonts\georgia italic.ttf'))
    pdfmetrics.registerFont(TTFont('Georgia Bold', 'fonts\georgia bold.ttf'))
    pdfmetrics.registerFont(TTFont('Georgia Bold Italic', 'fonts\Georgia Bold Italic font.ttf'))

    # 2nd positional param is bool flag for italic
    # 3rd positional param is bool flag for boldface
    addMapping('Georgia', 0, 0, 'Georgia')
    addMapping('Georgia', 0, 1, 'Georgia Italic')
    addMapping('Georgia', 1, 0, 'Georgia Bold')
    addMapping('Georgia', 1, 1, 'Georgia Bold Italic')


def generate_pdf(url: str) -> None:
    """
    Generate the PDF file from the given URL.
    :param url: A link to a fanfiction on a site such as fanfiction.net.
    """
    register_fonts()
    # Styling
    style = ParagraphStyle(
        name="Normal",
        fontSize=11.5,
        fontName="Georgia",
        leading=14.5
    )
    h1 = ParagraphStyle(
        name='Heading1',
        fontSize=14,
        leading=16,
        fontName="Georgia Bold",
        alignment=TA_CENTER
    )
    h2 = ParagraphStyle(
        name='Heading2',
        fontSize=12.5,
        leading=16,
        fontName="Georgia",
        alignment=TA_CENTER
    )

    # Create the document
    path = get_path(get_title(url) + '.pdf') # SimpleDocTemplate will take this as a parameter
    # and create a pdf file in the folder specified by get_path() with the specified name
    doc = SimpleDocTemplate(path, pagesize=letter,
                            rightMargin=72, leftMargin=72,
                            topMargin=40, bottomMargin=40)

    Story = []

    # Load in data
    lst_chap_names = get_chap_name(url)
    lst_chap_links = generate_links(url)
    profile_dict = get_profile(url)

    # Add fanfic title and the link to the original fanfic on Fanfiction.net
    Story.append(Paragraph(profile_dict['title'], h1))
    Story.append(Spacer(1, 12))
    # Add fanfic author
    Story.append(Paragraph("by " + "<font color='blue'><a href=" + profile_dict['author_link'] + "><u>" + profile_dict['author'] + "</u></a></font>", h2))
    Story.append(Spacer(1, 12))
    Story.append(Spacer(1, 12))
    # Add fanfic summary
    Story.append(Paragraph("<b>Summary</b>", style=style))
    Story.append(Spacer(1, 12))
    Story.append(Paragraph(profile_dict['summary'], style=style))
    Story.append(Spacer(1, 12))
    Story.append(Spacer(1, 12))
    Story.append(Spacer(1, 12))
    # <hr> line equivalent
    d = Drawing(100, 0.5) # parameters?
    d.add(Line(0, 20, 455, 20)) # (x1, y1, x2, y2)
    Story.append(d)

    Story.append(Paragraph("Originally posted at: " + "<font color='blue'><a href=" + lst_chap_links[0] + "><u>"
                           + lst_chap_links[0] + "</u></a></font>" + ".", style=style))
    Story.append(Spacer(1, 12))
    Story.append(Spacer(1, 12))

    # Add in fanfic stats
    Story.append(Paragraph("<strong>Rating: </strong>" + profile_dict['rating'], style=style))
    Story.append(Paragraph("<strong>Fandom: </strong>"+ profile_dict['fandom'], style=style))
    if profile_dict["genre"]:
        Story.append(Paragraph("<strong>Genre: </strong>" + profile_dict['genre'], style=style))
    if profile_dict["characters"]:
        Story.append(Paragraph("<strong>Characters: </strong>" + profile_dict['characters'], style=style))
    Story.append(Paragraph("<strong>Words: </strong>" + profile_dict['words'], style=style))
    if profile_dict["chapters"]:
        Story.append(Paragraph("<strong>Chapters: </strong>" + profile_dict['chapters'], style=style))
    Story.append(Paragraph("<strong>Published on: </strong>" + profile_dict['publication_date'], style=style))
    if profile_dict["updated_date"]:
        Story.append(Paragraph("<strong>Updated on: </strong>" + profile_dict['updated_date'], style=style))
    Story.append(Paragraph("<strong>Status: </strong>" + profile_dict['status'], style=style))


    Story.append(PageBreak())
    # Add in the fanfic
    for i in range(len(lst_chap_links)):
        Story.append(Spacer(1, 12))
        if lst_chap_names:
            Story.append(Paragraph(lst_chap_names[i], h1))
        Story.append(Spacer(1, 12))
        Story.append(Spacer(1, 12))
        lst_paragraphs = get_text_r(lst_chap_links[i])
        for paragraph in lst_paragraphs:
            Story.append(Paragraph(paragraph, style=style))
            Story.append(Spacer(1, 12))
        if len(lst_chap_links) - 1 != i:
            Story.append(PageBreak())

    Story.append(Spacer(1, 12))
    doc.build(Story)


# if __name__ == '__main__':
#   generate_pdf(" ")


