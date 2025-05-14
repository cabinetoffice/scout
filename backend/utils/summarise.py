import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

def get_most_important_words(text, num_important_words=3):
    """
    Identifies the most important words in a text based on frequency,
    excluding stopwords and punctuation.

    Args:
        text (str): The input string.
        num_important_words (int): The maximum number of important words to return.

    Returns:
        list: A list of the most important words, up to num_important_words.
    """
    if not text:
        return []

    stopWords = set(stopwords.words("english"))
    words = word_tokenize(text)
    freqTable = dict()

    for word in words:
        word = word.lower()
        if word in stopWords:
            continue
        # Filter out punctuation and non-alphabetic tokens
        if not word.isalpha(): # Use isalnum() if you want to include numbers as words
            continue
        freqTable[word] = freqTable.get(word, 0) + 1

    if not freqTable: # Handle cases where no valid words are found after filtering
        return []

    # Sort the frequency table by value (frequency) in descending order
    # freqTable.items() gives a list of (word, count) tuples
    # sorted() sorts them based on the count (item[1])
    sorted_freq_table = sorted(freqTable.items(), key=lambda item: item[1], reverse=True)

    # Extract the top 'num_important_words' words
    # item[0] is the word from the (word, count) tuple
    top_words = [item[0] for item in sorted_freq_table[:num_important_words]]

    return top_words
