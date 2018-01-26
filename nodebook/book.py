#!/usr/bin/env python -W ignore::DeprecationWarning
# -*- coding: utf-8 -*-
import spacy
import matplotlib as mpl
mpl.use('TkAgg')
import matplotlib.pyplot as plt
import networkx as nx
from tqdm import *
import json
import colorsys
import heapq
from formatbook import formatbook
from detectperson import detectperson
import urllib2
import uuid
import os
import re

import warnings
warnings.filterwarnings("ignore")


class book:
    nlp = spacy.load('en')
    interactions = []

    # Split a book file into an array of sentences and remove linebreaks.
    def _get_lines(self, file_path):
        with open(file_path, "r") as book_file:
            book_contents = book_file.read()
            unquoted = "\n".join(book_contents.replace("\n", " ").split('"')[0::2]).split(".")
            quoted = "\n".join(book_contents.replace("\n", " ").split('"')[1::2]).split(".")
            all = book_contents.replace("\n", " ").split(".")
        return [quoted, unquoted, all]

    # Filter out obvious place names, and names rediscovered as the same name but with punctuation.
    def _is_person(self, name):
        place_types = ["house", "lodge", "mount", "lane", "street", "place", "square", "st", "alley", "school", "shire"]
        try:
            name[0]
        except IndexError:
            return False
        if name[0].lower() == name[0] or name.lower() in ["mr", "mrs", "dr", "sir"]:
            return False
        for char in ["'s", "\"",u"’",u"”",u"“",".",",","!","?"]:
            if char in name:
                return False
        for n in name.split():
            if n.lower() in place_types:
                return False
        return True

    # Get a list of character names found in the book.
    def _extract_chars(self, book_lines, blacklist):
        char_dict = {}
        print("Looking for characters")
        for line in tqdm(book_lines):
            doc = self.nlp(unicode(line.decode("utf-8")))
            for ent in doc.ents:
                ent_text = ent.text.replace("\r", " ").replace("'", "").strip()
                if ent.label_ == "PERSON" and self._is_person(ent_text) and ent_text not in blacklist:
                    char_dict[ent_text] = char_dict.get(ent_text, 0) + 1
        char_list = [name for name, freq in char_dict.iteritems() if freq >= self.char_min_count]
        if self.is_first_person:
            char_list.append("[FP]")
        return char_list

    # Get a list of "duplicate" names, for example "Harry Potter" stored as both "Harry Potter", Harry" and "Potter".
    def _get_dup_list(self):
        dup_dict = {}
        for char1 in self.char_list:
            try:
                dup_dict[char1]
            except:
                dup_dict[char1] = [char1]
            char1_split = char1.split(" ")
            if len(char1_split) <= 1:
                continue
            for char2 in self.char_list:
                if char1 == char2:
                    continue
                if char2 in char1_split:
                    dup_dict[char1].append(char2)
        dup_lists = [l[1] for l in dup_dict.iteritems() if len(l[1]) > 1]
        return dup_lists

    # Contract duplicate nodes found in the dup list.
    def _merge_dups(self):
        dup_lists = self._get_dup_list()
        for list_ in dup_lists:
            for i in range(0, len(list_)-1):
                try:
                    self.G = nx.contracted_nodes(self.G, list_[i+1], list_[i])
                except KeyError:
                    continue

    # Determine whether two characters are connected by a transitive verb.
    def _subj_obj(self, char1, char2, doc, line):
        char1_subj = False
        char2_obj = False
        root_word = ""
        for child in doc:
            if child.dep_ == "ROOT":
                root_word = child.text
            if child.text == char1 and "subj" in child.dep_ and char1 in line:
                char1_subj = True
            if child.text == char2 and "obj" in child.dep_ or "conj" in child.dep_ and char2 in line:
                char2_obj = True
            if char1_subj and char2_obj:
                if (char1,char2,root_word) not in self.interactions:
                    self.interactions.append((char1,char2,root_word))
                return True
        return False

    # Determine whether two characters interact through one of the methods specified.
    def _interaction(self, char1, char2, line, measure):
        if measure == "same_line" and char1 in line and char2 in line:
            return True
        if measure == "verb":
            clauses = line.split(",")
            for clause in clauses:
                doc = self.nlp(unicode(clause.encode("utf-8").decode("utf-8")))
                if self._subj_obj(char1, char2, doc, clause) or self._subj_obj(char2, char1, doc, clause):
                    return True
        return False

    # Generate a graph from file.
    def _char_graph_from_file(self,lines,chars):
        found_chars = []
        interactions = {}
        tuple_keys = []
        G = nx.Graph()
        print("Extracting character relations")
        for line in tqdm(lines):
            line = unicode(line.decode("utf-8"))
            for char in chars:
                if char in line:
                    # Add character as node if unfound.
                    if char not in found_chars:
                        G.add_node(char)
                        found_chars.append(char)
                    # Add edges between the character and other characters if they're in the same sentence.
                    for c in chars:
                        if c != char and self._interaction(char, c, line, self.interaction_measure):
                            tuple_keys.append((char,c))
                            tuple_keys.append((c,char))
                            if c not in found_chars:
                                G.add_node(c)
                                found_chars.append(c)
                            G.add_edge(char,c)
                            tuple_key = (char,c)
                            interactions[tuple_key] = interactions.get(tuple_key, 0) + 1
                            G[char][c]['weight'] = interactions[tuple_key] # Update weight to be # interactions between the chars
        return G

    def _init_from_dump(self, file_path):
        with open(file_path, 'r') as f:
            data = json.load(f)
            nodes = data["nodes"]
            edges = data["edges"]
            weights = data["weights"]
            self.char_list = nodes
            self.G = nx.Graph()
            self.G.add_nodes_from(nodes)
            self.G.add_edges_from([(e[0],e[1]) for e in edges])
            self.is_first_person = ("[FP]" in nodes)
            for i,e in enumerate(self.G.edges()):
                self.G[e[0]][e[1]]["weight"] = weights[i]

    def _init_from_txt(self, file_path, char_min_count, interaction_measure, blacklist):
        self.char_min_count = char_min_count
        self.interaction_measure = interaction_measure

        get_lines = self._get_lines(file_path)
        quoted = formatbook().format(get_lines[0], True)
        self.book_lines = formatbook().format(get_lines[2], False)
        self.is_first_person = detectperson().is_1stperson(quoted)
        self.char_list = self._extract_chars(self.book_lines, blacklist)
        self.G = self._char_graph_from_file(self.book_lines, self.char_list)
        self._merge_dups()

    def _init_from_url(self, file_path, char_min_count, interaction_measure, blacklist):
        from_gutenberg = ("gutenberg.org/" in file_path)
        response = urllib2.urlopen(file_path)
        body = response.read()
        if from_gutenberg:
            body = body.split('*** END OF THIS PROJECT GUTENBERG EBOOK')[0]
        temp_name = str(uuid.uuid4()) + ".txt"
        temp_path = "tmp/" + temp_name
        temp_txt = open(temp_path, "w")
        temp_txt.write(body)
        temp_txt.close()
        self._init_from_txt(temp_path, char_min_count, interaction_measure, blacklist)
        os.remove(temp_path)

    def __init__(self, file_path=None, char_min_count=3, interaction_measure="same_line", blacklist=[], start_line=0, merge_fp= False):
        self.start_line = start_line
        self.merge_fp = merge_fp
        from_dump = (file_path.split(".")[-1] == 'json')
        from_url = (file_path[0:7] == "http://") or (file_path[0:8] == "https://")
        self.proportions = {}

        if from_dump:
            self._init_from_dump(file_path)
        elif not from_dump and not from_url:
            self._init_from_txt(file_path, char_min_count, interaction_measure, blacklist)
        elif from_url:
            self._init_from_url(file_path, char_min_count, interaction_measure, blacklist)

        fp_overlaps = detectperson().all_overlaps(self.G)
        if self.is_first_person:
            biggest_overlap = heapq.nlargest(1, fp_overlaps, key=fp_overlaps.get)[0][1]
            if self.degree("[FP]") >= self.degree(biggest_overlap):
                self.char_list.remove(biggest_overlap)
                self.first_person = biggest_overlap
                if self.merge_fp: self.G = nx.contracted_nodes(self.G, "[FP]", self.first_person)
            else:
                self.first_person = None
        else:
            self.first_person = None

        deg_list = [self.degree(node) for node in self.G.nodes()]
        try:
            max_deg = float(max(deg_list))
        except ValueError:
            raise ValueError('No nodes in graph. Try changing char_min_count to a lower value.')
        for node in self.G.nodes():
            self.proportions[node] = self.degree(node)/max_deg

    # Dump book to JSON file
    def dump(self, cache_file):
        weights = []
        open(cache_file, 'w').close()
        with open(cache_file, 'a') as outfile:
            for e in self.G.edges():
                weights.append(self.G[e[0]][e[1]]["weight"])
            json.dump({"nodes":self.G.nodes(), "edges":self.G.edges(), "weights":weights}, outfile)

    def degree(self,char):
        return len(self.G.neighbors(char))

    def _get_color(self, red_to_green):
        assert 0 <= red_to_green <= 1
        # in HSV, red is 0 deg and green is 120 deg (out of 360);
        # divide red_to_green with 3 to map [0, 1] to [0, 1./3.]
        hue = red_to_green / 3.0
        r, g, b = colorsys.hsv_to_rgb(hue, 1, 1)
        return map(lambda x: int(255 * x), (r, g, b))

    def _rgb_to_hex(self, red, green, blue):
        """Return color as #rrggbb for the given color values."""
        return '#%02x%02x%02x' % (red, green, blue)

    def important_characters(self, num, metric="degree"):
        if metric == "degree":
            rank_dict = self.proportions
        elif metric == "clustering":
            rank_dict = nx.clustering(self.G)
        elif metric == "centrality":
            rank_dict = nx.betweenness_centrality(self.G)
        return heapq.nlargest(num, rank_dict, key=rank_dict.get)

    def graph(self, with_labels=True, node_size=400):
        pos=nx.spring_layout(self.G)
        nx.draw(self.G, pos, node_size=node_size, with_labels=with_labels, font_size=8, alpha=0)
        weight_list = [d["weight"] for u,v,d in self.G.edges(data=True)]
        max_weight = float(max(weight_list))

        for node in self.G.nodes():
            degree_proportion = self.proportions[node]
            rgb_color = self._get_color(1 - degree_proportion)
            hex_color = self._rgb_to_hex(rgb_color[0],rgb_color[1],rgb_color[2])
            nx.draw_networkx_nodes(self.G,pos,nodelist=[node],
                node_color=hex_color,node_size=node_size,
                alpha=0.7 + 0.3*degree_proportion)

        edge_labels=dict([((u,v,),d['weight'])
                     for u,v,d in self.G.edges(data=True)])
        plt.figure(1,figsize=(15,15))
        for edge in self.G.edges(data=True):
            nx.draw_networkx_edges(self.G,pos, edgelist=[(edge[0],edge[1])], width=1.0, alpha=0.5 + 0.5*(edge[2]["weight"]/max_weight))
        plt.show()
