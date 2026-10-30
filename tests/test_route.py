import pytest

from keith.importers import route
from keith.models import Book

orth = Book(1, "Orthodoxy", "t", "t")
thurs = Book(2, "The Man Who Was Thursday", "t", "t")
BOOKS = [orth, thurs]


@pytest.mark.parametrize("text, active, book, category, out", [
    ("#orthodoxy #character Syme is a poet", None, "Orthodoxy", "character", "Syme is a poet"),
    ("Syme #ORTHODOXY is a poet", None, "Orthodoxy", "idea", "Syme is a poet"),
    ("#the-man-who-was-thursday #place Saffron Park", None, "The Man Who Was Thursday", "place", "Saffron Park"),
    ("untagged thought", "Orthodoxy", "Orthodoxy", "idea", "untagged thought"),
    ("untagged thought", None, None, "idea", "untagged thought"),
    ("#orthodoxy #the-man-who-was-thursday both", None, None, "idea",
     "#orthodoxy #the-man-who-was-thursday both"),
    ("#idea #place first category wins", "Orthodoxy", "Orthodoxy", "idea", "first category wins"),
    ("learn C# and see issue#4 page#intro", "Orthodoxy", "Orthodoxy", "idea",
     "learn C# and see issue#4 page#intro"),
    ("#todo keep unknown tags #orthodoxy", None, "Orthodoxy", "idea", "#todo keep unknown tags"),
    ("line one #orthodoxy\nline two", None, "Orthodoxy", "idea", "line one\nline two"),
])
def test_route(text, active, book, category, out):
    active_book = next((b for b in BOOKS if b.title == active), None)
    r = route(text, BOOKS, active_book)
    assert (r.book.title if r.book else None) == book
    assert r.category == category
    assert r.text == out


def test_category_names_are_reserved():
    outline = Book(3, "Outline", "t", "t")
    r = route("#outline plot", [outline], None)
    assert (r.book, r.category) == (None, "outline")


def test_tag_matching_two_books_goes_to_inbox():
    a, b = Book(1, "Orthodoxy", "t", "t"), Book(2, "Orthodoxy!", "t", "t")
    assert route("#orthodoxy x", [a, b], None).book is None
