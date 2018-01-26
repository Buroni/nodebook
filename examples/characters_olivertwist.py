# Do some analysis determining the most central characters in Oliver Twist, and figure out
# whether the book is written in first or third person.

from nodebook import book

olivertwist = book("http://www.gutenberg.org/files/47529/47529-0.txt")

important_characters = olivertwist.important_characters(8)

pov = "first person" if olivertwist.is_first_person else "third person"

print("Most central characters: %s" % important_characters)

print("Point of view: %s" % pov)
