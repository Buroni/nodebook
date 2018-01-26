# Load Dorian Gray and dump into a json file which can be loaded quickly using book('mobydick.json'), and graph the character relations.

from nodebook import book

doriangray = book("http://www.gutenberg.org/cache/epub/174/pg174.txt")

doriangray.dump("doriangray.json")

doriangray.graph()
