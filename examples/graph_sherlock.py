# Make a graph of character interactions in Sherlock Holmes. Note that 'London' is mistakenly
# identified as a character. Try to eliminate this by adding it to the blacklist or playing with the
# min_char_count parameter.

from nodebook import book

sherlock = book("http://www.gutenberg.org/cache/epub/1661/pg1661.txt")

sherlock.graph(with_labels=True, node_size=200)
