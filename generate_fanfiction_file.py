from requests import get
from requests.exceptions import RequestException
from contextlib import closing
from bs4 import BeautifulSoup
from typing import List, Dict
from collections import OrderedDict
from reportlab.pdfgen import canvas

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
        if option_tags is not None:
            values = [o.get('value') for o in option_tags.find_all("option")] # AttributeError: 'NoneType' object has no attribute 'find_all'; create a check for html.find("select") first. What does find() return?
            return values[-1]
        else:
            # print(1)
            return 1
        # values = [o.get('value') for o in option_tags]
        # print(values)
        # unique_values = list(OrderedDict.fromkeys(values))  # a soln to the duplicate items in list issue. alternatively: select the first occurrence of option
        # print(unique_values)
        # one-chapter situation
        # if not values:
        #     return 1
        # # multi-chapter situation
        # else:
        #     print(values[-1])
        #     return values[-1]
            # print(int(unique_values[-1]))
            # return int(unique_values[-1])

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
        # iteration = 0

        # for option in option_tags.find("option"):

        # l = []
        if option_tags is not None:
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
        # print(option_tags)
        # print(option_lst)

        # unique_option_tags = list(OrderedDict.fromkeys(option_tags))

        # print(option_tags)
        # print(unique_option_tags)

        # chap_names = [o.text for o in unique_option_tags]

        # for o in option_tags:
        #     print(option_tags)
        #     print(o)
        #     print(o.text)

        # unique_chap_names = list(OrderedDict.fromkeys(chap_names))

        # one-chapter situation
        else:
            return []
        # multi-chapter situation
            # print(unique_chap_names)
            # print(chap_names)
            # return unique_chap_names

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


def get_text(url: str)-> str:
    """
    Downloads the fanfiction page(s) and returns a string of the entire text of the chapter(s).
    """
    lst_links = generate_links(url)
    text = ''
    for link in lst_links:
        response = simple_get(link)
        if response is not None:
            html = BeautifulSoup(response, 'html.parser')
            for paragraph in html.select('p'):
                text += paragraph.get_text() + '\n'
        else:
            #Raise an exception if we failed to get any data from the url
            raise Exception('Error retrieving contents at {}'.format(url))
    # print(text)
    return text


# List[List] vs. Dict[str, List]
# def get_text_dict(url: str)-> Dict:
#     """
#     Downloads the fanfiction page(s) and returns a dictionary, with the key being the chapter's title,
#     and the value being a list of text.
#     """
#     lst_links = generate_links(url)
#     text_dict = {}
#     for link in lst_links:
#         response = simple_get(link)
#         if response is not None:
#             html = BeautifulSoup(response, 'html.parser')
#             for paragraph in html.select('p'):
#                 # text_dict[].append(paragraph.get_text())
#         else:
#             # Raise an exception if we failed to get any data from the url
#             raise Exception('Error retrieving contents at {}'.format(url))
#     # print(text_dict)
#     return text_dict

def generate_pdf(url: str) -> None:
    c = canvas.Canvas(get_title(url) + '.pdf')
    c.drawString(100, 750, get_text(url))
    c.save()

def cursormoves1(canvas):
    from reportlab.lib.units import inch
    textobject = canvas.beginText()
    textobject.setTextOrigin(inch, 2.5*inch)
    textobject.setFont("Helvetica-Oblique", 14)
    # for line in lyrics:
    #     textobject.textLine(line)
    textobject.textline('Hello World!')
    textobject.setFillGray(0.4)
    textobject.textLines('''
    With many apologies to the Beach Boys
    and anyone else who finds this objectionable
    ''')
    canvas.drawText(textobject)


from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def textobject_demo(url: str):
    my_canvas = canvas.Canvas(get_title(url) + '.pdf',
                              pagesize=letter)
    # Create textobject
    textobject = my_canvas.beginText()

    # Set text location (x, y)
    textobject.setTextOrigin(100, 730)

    # Set font face and size
    textobject.setFont('Times-Roman', 12)

    # Write a line of text + carriage return
    textobject.textLine(text=get_text(url))

    # Change text color
    textobject.setFillColor(colors.red)

    # # Write red text
    # textobject.textLine(text='Python rocks in red!')

    # Write text to the canvas
    my_canvas.drawText(textobject)

    my_canvas.save()

if __name__ == '__main__':
    # get_text("https://m.fanfiction.net/s/5182916/1/a-fish") # ISSUES with finding num of chapter because it's the mobile page. "m.fanfiction.."
   
    # stopped at the end of chapter 5
    # get_text("https://www.fanfiction.net/s/7880959/1/Ad-Infinitum") # ISSUE UnicodeEncodeError: 'charmap' codec can't encode character '\u2015' in position 0: character maps to <undefined>
    # cursormoves1(canvas)
    # textobject_demo("https://www.fanfiction.net/s/5182916/1/a-fish")

    # get_num_of_chapters("https://www.fanfiction.net/s/5182916/1/a-fish")
    # get_chap_name("https://www.fanfiction.net/s/5182916/1/a-fish")

    # generate_pdf("https://www.fanfiction.net/s/5182916/1/a-fish")
    # get_num_of_chapters("https://www.fanfiction.net/s/6483376/1/Sparks-Fly-Tires-Skid")
    get_num_of_chapters("https://www.fanfiction.net/s/8383682/1/i-ll-write-you-harmony-in-c")
    get_chap_name("https://www.fanfiction.net/s/8383682/1/i-ll-write-you-harmony-in-c")
    # get_num_of_chapters("https://www.fanfiction.net/s/10079742/1/The-Shepard")
    # get_chap_name("https://www.fanfiction.net/s/10079742/1/The-Shepard")

    # get_text("https://www.fanfiction.net/s/5182916/1/a-fish")
    # simple_get("https://www.fanfiction.net/s/5182916/1/a-fish")

#TODO: convert .txt to .docx or .pdf, never take in mobile version of fanfiction.net, UnicodeEncodeError, include Chapter number and title in the .txt file
