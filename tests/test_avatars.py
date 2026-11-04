from app.services.avatars import initials


def test_two_words_give_two_initials():
    assert initials("Kevin_M") == "KM"
    assert initials("awa-traore") == "AT"


def test_single_word_gives_first_two_letters():
    assert initials("Awa") == "AW"
    assert initials("P") == "P"
