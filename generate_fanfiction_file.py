import os
from requests import get
from requests.exceptions import RequestException
from contextlib import closing
from bs4 import BeautifulSoup
from typing import List, Dict
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
        # option_tags = html.select("option")  # research select vs. find vs. find_all; find returns the first occurrence
        option_tags = html.find("select")
        # print(option_tags)
        if option_tags is not None: #multi-chapter situation
            values = [o.get('value') for o in option_tags.find_all("option")] # AttributeError: 'NoneType' object has no attribute 'find_all'; create a check for html.find("select") first. What does find() return?
            return int(values[-1])
        else: #one-chapter situation
            return 1

        # unique_values = list(OrderedDict.fromkeys(values))  # a soln to the duplicate items in list issue. alternatively: select the first occurrence of option


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
    # print(normal_title)
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
        # option_tags = html.select_one("select")

        option_tags = html.find("select", attrs={"id": "chap_select"})
        # chap_names = [o.text for o in option_tags.find_all("option")]

        # for option in option_tags.find_all("option"):
        #     print(option.get_text())
        #     print(option.next_sibling)
        # for option in option_tags.find("option"):
        if option_tags is not None: # multi-chapter situation
            for option in option_tags:
                # iteration += 1
                # if iteration == 3:
                #     return
                # print(option_tags)
                # l.append(option.get_text(' '))
                text = option.get_text('|||') # ||| as a unique marker to later split by
                lst_chap_names = text.split('|||')
                # print(lst_chap_names)
                return lst_chap_names
                # print(option)
                # print(option.get_text(' '))

        # option_lst = [print(option) for option in option_tags]
        # unique_option_tags = list(OrderedDict.fromkeys(option_tags))

        # chap_names = [o.text for o in unique_option_tags]

        # for o in option_tags:
        #     print(option_tags)
        #     print(o)
        #     print(o.text)

        # unique_chap_names = list(OrderedDict.fromkeys(chap_names))

        else: # one-chapter situation
            return []
    else:
        # Raise an exception if we failed to get any data from the url
        raise Exception('Error retrieving contents at {}'.format(url))


#Select and extract from the raw HTML using BeautifulSoup, to get text
# The BeautifulSoup constructor parses raw HTML strings and produces an object that mirrors the HTML document's structure
# The object includes a lot of methods to select, view, and manipulatethe DOM nodes and text content
#Extract the textual content of a chapter:


def generate_txt(url: str)-> None:
    """
    Downloads the fanfiction page(s) and save it as a .txt file.
    """
    lst_links = generate_links(url)
    title = get_title(url)
    f = open(title + ".txt", 'w+', encoding='utf-8')
    for link in lst_links:
        response = simple_get(link)
        if response is not None:
            html = BeautifulSoup(response, 'html.parser')
            for paragraph in html.select('p'): 
                f.write(paragraph.get_text() + '\r\n')
        else:
            #Raise an exception if we failed to get any data from the url
            raise Exception('Error retrieving contents at {}'.format(url))
    f.close()

# all chapter links were generated inside the get_text function
# def get_text(url: str)-> str:
#     """
#     Downloads the fanfiction page(s) and returns a string of the entire text of the chapter(s).
#     """
#     lst_links = generate_links(url)
#     text = ''
#     for link in lst_links:
#         response = simple_get(link)
#         if response is not None:
#             html = BeautifulSoup(response, 'html.parser')
#             for paragraph in html.select('p'):
#                 text += paragraph.get_text() + '\n'
#         else:
#             #Raise an exception if we failed to get any data from the url
#             raise Exception('Error retrieving contents at {}'.format(url))
#     # print(text)
#     return text

#each time get_text() is called, it returns all the text as a single string from the given URL
# def get_text(url: str)-> str:
#     """
#     Downloads the fanfiction page(s) and returns a string of the entire text of the chapter(s).
#     """
#     text = ''
#     response = simple_get(url)
#     if response is not None:
#         html = BeautifulSoup(response, 'html.parser')
#         for paragraph in html.select('p'):
#             text += paragraph.get_text() + '\n'
#     else:
#         #Raise an exception if we failed to get any data from the url
#         raise Exception('Error retrieving contents at {}'.format(url))
#     # print(text)
#     return text


#Previous current function in use
# def get_text(url: str)-> List:
#     """
#     Downloads the fanfiction page and returns a list of all the paragraphs in a chapter.
#     """
#     lst_p = []
#     response = simple_get(url)
#     if response is not None:
#         html = BeautifulSoup(response, 'html.parser')
#         for paragraph in html.select('p'):
#             # lst_p.append(paragraph.get_text()) # works, but doesn't preserve italics and bolded text
#             stringify_replace = str(paragraph).replace("<p>", "", 1).replace("</p>", "", 1).\
#                 replace('<span style="text-decoration:underline;">', "").\
#                 replace('<span style="text-decoration: underline;">', "").replace("</span>", "").\
#                 replace('<p align="center">', "")
#             lst_p.append(stringify_replace)
#     else:
#         #Raise an exception if we failed to get any data from the url
#         raise Exception('Error retrieving contents at {}'.format(url))
#     # print(lst_p)
#     return lst_p


def get_text(url: str)-> List:
    """
    Downloads the fanfiction page and returns a list of all the paragraphs in a chapter.
    """
    lst_text = []
    response = simple_get(url)
    if response is not None:
        html = BeautifulSoup(response, 'html.parser')
        story = html.find("div", attrs={"id": "storytext"})
        # print(story)
        if story is None:
            story = html.find("div", attrs={"id": "storycontent"})
        # if story.find("p") is not None:
        # if '<p>' or '</p>' in story:
        #     print('p tag exists') # should not print for Tales of the House of the Moon, but it did.
        # print(story.get_text())

            # for paragraph in story.find_all('p'):
            # for paragraph in html.select("p"):
        for line in story:
            # print(line)
            if line.name == 'p':
                stringify_replace = str(line).replace("<p>", "").replace("</p>", "").\
                    replace('<p align="center">', "").replace('<p align="center;">', "").\
                    replace('<p style="text-align:center;">', "").\
                    replace('<span style="text-decoration:underline;">', "").\
                    replace('<span style="text-decoration: underline;">', "<u>").replace("</span>", "</u>")
                lst_text.append(stringify_replace)
                # print(stringify_replace)

                # print(stringify_replace)
            # if line.find("span") is not None:
            #     stringify_replace = stringify_replace.replace('<span style="text-decoration:underline;">', "").\
            #         replace('<span style="text-decoration: underline;">', "<u>").replace("</span>", "</u>")
            else:
                if str(line) != '\n':
                    stringify_replace = str(line).replace("<br>", "").replace("</br>", "").replace("<br/>", "")\
                        .replace("<center>", "").replace("</center>", "").replace("<br>", ""). \
                        replace("</br>", "").strip()
                    # .replace("\\r\\n", "").replace("\\n", "").replace("\n", "").replace("\\r", "").\
                    # replace("\r", "").replace("\r\n", "")
                    lst_text.append(stringify_replace)
                    # print(stringify_replace)
                # print(id(lst_text))
        # else:
        #     for line in story:
        #         stringify_replace = str(line).replace("<center>", "").replace("</center>", "").replace("<br>", "").\
        #             replace("</br>", "").replace("\\r\\n", "").replace("\\n", "").replace("<br>", "").replace("</br>", "").replace("<br/>", "")
                # print(stringify_replace)
                # lst_text.append(stringify_replace)
        # for paragraph in html.select('p'):
        #     # lst_p.append(paragraph.get_text()) # works, but doesn't preserve italics and bolded text
        #     stringify_replace = str(paragraph).replace("<p>", "", 1).replace("</p>", "", 1).\
        #         replace('<span style="text-decoration:underline;">', "").\
        #         replace('<span style="text-decoration: underline;">', "").replace("</span>", "").\
        #         replace('<p align="center">', "")
        #     lst_p.append(stringify_replace)
    else:
        #Raise an exception if we failed to get any data from the url
        raise Exception('Error retrieving contents at {}'.format(url))
    # print(list(filter(None, lst_text)))
    # print(lst_text)
    # print(id(lst_text))
    lst_text = list(filter(None, lst_text))
    # print(id(lst_text))
    # print(lst_text)
    return lst_text # shouldn't this return be in the if branch?


# def get_genre() -> List:
#     """
#     Return a list of all possible genres listed in fanfiction.net for a fanfic.
#     From an arbitrary URL of a fanfiction page where a selection of all genres are listed.
#     """
#     url = "https://www.fanfiction.net/community/The-XX-Collective-Strong-Intelligent-Kickass-Women-in-Fanfiction/125666/"
#     response = simple_get(url)
#     if response is not None:
#         html = BeautifulSoup(response, 'html.parser')
#         genres = html.find("select", attrs={"name": "genreid"})
#         lst_genres = genres.find('option').get_text('||').split('||')
#         del lst_genres[0]
#         # lst_genres = [genre.text for genre in genres.find('option')] # AttributeError: 'NavigableString' object has no attribute 'text'
#     print(lst_genres)
#     return lst_genres
#     test = 'Chapters: 6'
#     if '6' in test:
#         print('true')
#     else:
#         print('false')
#       if 'Romance' in 'Romance/Adventure':
#           print('true')
#       else:
#           print('false')


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
            if stats_split[2].split("/")[0] in genres:
                genre = stats_split[2]
                chapters = "1"
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
        words = words_split[1]

            # for i, s in enumerate(stats_split):
            #     if 'Chapters:' in s:
            #         # print(i)
            #         chapters_split = stats_split[i].split(
            #             ":")  # split() bc I only need the number --- 'Chapters: number"
            #         chapters = chapters_split[1].strip()
            #         words_split = stats_split[i + 1].split(":")
            #         for g in genres:
            #
            #             if g in stats_split[i-2]:
            #                 print(stats_split[i-2])
            #                 genre = stats_split[i-2]
            #                 characters = stats_split[i-1]
            #                 break
            #             elif g in stats_split[i-1]:
            #                 genre = stats_split[i-1]
            #                 characters = ''
            #                 break
            #             elif stats_split[i-1] == stats_split[1]:
            #                 characters = ''
            #                 genre = ''
            #                 break
                        # elif stats_split[i-1] != stats_split[1]:
                        #     print('aahha')
                        #     characters = stats_split[i-1]
                        #     genre = ''
                        #     break
        # else: # profile key 'Chapters' doesn't exist
        #     chapters = "1"
        #     for g in genres:
        #         if g in stats_split[2]:
        #             genre = stats_split[2]
        #             if "Words:" in stats_split[3]:
        #                 words_split = stats_split[3].split(":")
        #                 characters = ''
        #             else:
        #                 characters = stats_split[3]
        #                 words_split = stats_split[4].split(":")
        #             break
        #         else:
        #             genre = ''
        #             if "Words:" in stats_split[2]:
        #                 words_split = stats_split[2].split(":")
        #                 characters = ''
        #             else:
        #                 print('why')
        #                 characters = stats_split[2]
        #                 words_split = stats_split[3].split(":")
        #             break
        # words = words_split[1]

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
        lst_paragraphs = get_text(lst_chap_links[i])
        for paragraph in lst_paragraphs:
            Story.append(Paragraph(paragraph, style=style))
            Story.append(Spacer(1, 12))
        Story.append(PageBreak())
        # Story.append(Paragraph(str(i), style=style))

    Story.append(Spacer(1, 12))
    doc.build(Story)


if __name__ == '__main__':
   # generate_pdf("https://www.fanfiction.net/s/1638751/1/Tales-From-the-House-of-the-Moon") # No <p> tags wtf; RecursionError: maximum recursion depth exceeded in comparison
   # get_text("https://www.fanfiction.net/s/1638751/18/Tales-From-the-House-of-the-Moon")
   # generate_pdf("https://www.fanfiction.net/s/6379811/1/The-Fourth-King")
   # get_text("https://m.fanfiction.net/s/360519/1/Chimera")
   #  get_text("https://m.fanfiction.net/s/3504281/1/Sky-on-Fire-I-Slow-Burn")
   # get_text("https://www.fanfiction.net/s/11456734/1/Problem-Nine-And-Two")
   # generate_pdf("https://www.fanfiction.net/s/11456734/1/Problem-Nine-And-Two")
   # get_text("https://www.fanfiction.net/s/1638751/2/Tales-From-the-House-of-the-Moon")
   # generate_pdf("https://www.fanfiction.net/s/4844985/1/brave-soldier-girl-comes-marching-home")
   # get_text("https://www.fanfiction.net/s/4844985/1/brave-soldier-girl-comes-marching-home")

#TODO: never take in mobile version of fanfiction.net, UnicodeEncodeError, PDF chapter links,
# boxy stats, new <p></p> tag removal method, japanese characters, understand split() better, optimize, brave girl coming home repition of text, extra page at the end Brave girl ..., div with no p tags, div with p tags,
# tales from the house of the moon - chapter 18, 21 -- for line in story, line is acting like a nested paragraph. So all paragraphs are appended at once. UGHHH
# I don't preserver centering of origianl text
# ReportLab doesn't support <center> and <br> tags (and \r\n or \n ?) it does support \r and \n
