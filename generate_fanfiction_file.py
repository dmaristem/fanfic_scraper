from requests import get
from requests.exceptions import RequestException
from contextlib import closing
from bs4 import BeautifulSoup
from typing import List, Dict
from collections import OrderedDict
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.fonts import addMapping
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import inch


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
        print(option_tags)
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

        option_tags = html.find("select")
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
                print(lst_chap_names)
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

# each time get_text() is called, it returns all the text as a single string from the given URL
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

def get_text(url: str)-> str:
    """
    Downloads the fanfiction page(s) and returns a string of the entire text of the chapter(s).
    """
    lst_p = []
    response = simple_get(url)
    if response is not None:
        html = BeautifulSoup(response, 'html.parser')
        for paragraph in html.select('p'):
            lst_p.append(paragraph.get_text())
    else:
        #Raise an exception if we failed to get any data from the url
        raise Exception('Error retrieving contents at {}'.format(url))
    print(lst_p)
    return lst_p

def generate_pdf(url: str) -> None:
    # Registering the desired font
    pdfmetrics.registerFont(TTFont('Georgia', 'Georgia Regular font.ttf'))
    pdfmetrics.registerFont(TTFont('Georgia Italic', 'georgia italic.ttf'))
    pdfmetrics.registerFont(TTFont('Georgia Bold', 'georgia bold.ttf'))
    pdfmetrics.registerFont(TTFont('Georgia Bold Italic', 'Georgia Bold Italic font.ttf'))

        # 2nd positional param is bool flag for italic
        # 3rd positional param is bool flag for boldface
    addMapping('Georgia', 0, 0, 'Georgia')
    addMapping('Georgia', 0, 1, 'Georgia Italic')
    addMapping('Georgia', 1, 0, 'Georgia Bold')
    addMapping('Georgia', 1, 1, 'Georgia Bold Italic')

    # Styling
    style = ParagraphStyle(
        name="Normal",
        fontSize=11.5,
        fontName="Georgia",
        leading=15
    )
    h1 = ParagraphStyle(
        name='Heading1',
        fontSize=14,
        leading=16,
        fontName="Georgia Bold",
        alignment=TA_CENTER
    )

    # Create the document
    doc = SimpleDocTemplate(get_title(url) + '.pdf', pagesize=letter,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=18)

    Story = []
    lst_chap_names = get_chap_name(url)
    lst_chap_links = generate_links(url)

    for i in range(len(lst_chap_names)):
        Story.append(Spacer(1, 12))
        Story.append(Paragraph(lst_chap_names[i], h1))
        Story.append(Spacer(1, 12))
        Story.append(Spacer(1, 12))
        lst_paragraphs = get_text(lst_chap_links[i])
        for paragraph in lst_paragraphs:
            Story.append(Paragraph(paragraph, style=style))
            Story.append(Spacer(1, 12))

    Story.append(Spacer(1, 12))
    doc.build(Story)


if __name__ == '__main__':
    # get_text("https://m.fanfiction.net/s/5182916/1/a-fish") # ISSUES with finding num of chapter because it's the mobile page. "m.fanfiction.."
    # stopped at the end of chapter 5
    # get_text("https://www.fanfiction.net/s/7880959/1/Ad-Infinitum") # ISSUE UnicodeEncodeError: 'charmap' codec can't encode character '\u2015' in position 0: character maps to <undefined>

    generate_pdf("https://www.fanfiction.net/s/10079742/1/The-Shepard")
    # generate_pdf("https://www.fanfiction.net/s/5182916/1/a-fish")


#TODO: never take in mobile version of fanfiction.net, UnicodeEncodeError, include Chapter number and title in the .txt file
