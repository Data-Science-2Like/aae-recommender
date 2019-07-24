import collections

import matplotlib

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

from aaerec.datasets import Bags
from eval.aminer import unpack_papers, papers_from_files
from eval.fiv import load, unpack_papers as unpack_papers_fiv
from eval.mpd.mpd import playlists_from_slices, unpack_playlists

matplotlib.use('agg')

# Possible values: pubmed, dblp, acm, swp, rcv, econbiz, mpd
dataset = "pubmed"
# only papers/labels with at least min_x_cit citations/occurrences
# in the plot of the distribution of papers/labels by citations/occurrences
# Set to 0 if not relevant
min_x_cit = 10
# only papers/labels with at most man_x_cit citations/occurrences
# in the plot of the distribution of papers/labels by citations/occurrences
# Set to None if not relevant
max_x_cit = 100
# Shows the y-value at the given mark_x_cit
# Set to None if not relevant
mark_x_cit = 50
# only papers/labels with at least min_x_cit citations/occurrences
# in the plot of the distribution of papers/labels by citations/occurrences
# Set to 0 if not relevant
min_x_set = 0
# only papers/labels with at most man_x_cit citations/occurrences
# in the plot of the distribution of papers/labels by citations/occurrences
# Set to None if not relevant
max_x_set = 500
# Shows the y-value at the given mark_x_cit
# Set to None if not relevant
mark_x_set = 100
# Only papers from min_year
min_year = 1970


def compute_stats(A):
    return A.shape[1], A.min(), A.max(), np.median(A, axis=1)[0, 0], A.mean(), A.std()


def plot(objects, dataset, x_dim, y_dim, x=None):
    plt.bar(objects.keys(), objects.values(), align='center', alpha=0.5)
    plt.ylabel(y_dim)
    plt.xlabel(x_dim)

    # print the y value of bar at a given x
    if x != None:
        for x_i, y_i in enumerate(objects.values()):
            if x_i == x:
                print("For x={} y={}".format(x, y_i))
                plt.text(x_i, y_i, str(y_i) + "\n", ha='center')

    plt.savefig('papers_by_{}_{}.pdf'.format(x_dim.replace(" ", "_"), dataset))
    # plt.show()
    plt.close()


def paper_by_n_citations(citations):
    '''
    From a dictionary with paper IDs as keys and citation numbers as values
    to a dictionary with citation numbers as keys and paper numbers as values
    '''
    papers_by_citations = {}
    for paper in citations.keys():
        try:
            papers_by_citations[citations[paper]] += 1
        except KeyError:
            papers_by_citations[citations[paper]] = 1

    return papers_by_citations


def from_to_key(objects, min_key, max_key=None):
    '''
    From a dictionary create a new dictionary with only items with key greater
    than min_key and optionally smaller than max_key. If min_key = max_key,
    it returns a dictionaly with only that key
    '''
    print("Filtering dictionary's keys from {} to {}".format(min_key, max_key))
    # It assumes only positive integers as keys
    if max_key != None and max_key < min_key:
        print("Error: max_key has to be greater than min_key. Dictionary unchanged")
        return objects

    if max_key == None and min_key <= 0:
        print("Warning: min_key lower or equal to 0 and no max_key has no effect."
              + "Dictionary unchanged")
        return objects

    if max_key != None:
        return {x: objects[x] for x in objects if x >= min_key and x <= max_key}

    return {x: objects[x] for x in objects if x >= min_key}


def generate_years_citations_set_cnts(papers, dataset):
    '''
    Return the distribution of papers by years and by citations
    '''
    years, citations, set_cnts = {}, {}, {}

    for paper in papers:
        try:
            years[paper["year"]] += 1
        except KeyError:
            # MPD has no time information (no year)
            if "year" not in paper.keys() and dataset != "mpd":
                # skip papers without a year
                # unless dataset is MPD, which has no year
                continue
            if dataset != "mpd":
                years[paper["year"]] = 0
        if dataset == "dblp":
            # DBLP has the citations for each paper
            try:
                citations[paper["n_citation"]] += 1
            except KeyError:
                citations[paper["n_citation"]] = 1
            try:
                set_cnts[paper["id"]] = len(paper["references"])
            except KeyError:
                set_cnts[paper["id"]] = 0
        elif dataset == "acm":
            # For ACM we need to compute the citations for each paper
            if "references" not in paper.keys():
                continue
            for ref in paper["references"]:
                try:
                    citations[ref] += 1
                except KeyError:
                    citations[ref] = 1
            set_cnts[paper["id"]] = len(paper["references"])
        elif dataset == "swp":
            # For SWP we need to compute the occurrences for each subject
            if "subjects" not in paper.keys():
                continue
            for subject in paper["subjects"]:
                try:
                    citations[subject] += 1
                except KeyError:
                    citations[subject] = 1
            set_cnts[paper["id"]] = len(paper["subjects"])
        else:
            # For MPD we need to compute the occurrences for each track
            for track in paper["tracks"]:
                try:
                    citations[track["track_uri"]] += 1
                except KeyError:
                    citations[track["track_uri"]] = 1
            set_cnts[paper["pid"]] = len(paper["tracks"])

    return years, citations, set_cnts


def generate_citations(df):
    citations = {}

    for index, paper in df.iterrows():
        for ref in paper["set"].split(","):
            if ref == "":
                continue
            try:
                citations[ref] += 1
            except KeyError:
                citations[ref] = 1

    return citations


def set_count(df):
    set_cnts = {}

    for index, paper in df.iterrows():
        set_cnts[paper["owner"]] = len(paper["set"].split(","))

    return set_cnts


def set_path(ds):
    if ds == "dblp" or ds == "acm":
        p = '/data22/ivagliano/aminer/'
        p += ("dblp-ref/" if ds == "dblp" else "acm.txt")
    elif ds == "swp":
        p = "/data22/ivagliano/SWP/FivMetadata_clean.json"
    elif ds == "mpd":
        p = "/data21/lgalke/datasets/MPD/data/"
    elif ds == "pubmed":
        p = "/data21/lgalke/datasets/PMC/citations_pmc.tsv"
    elif ds == "econbiz":
        p = "/data21/lgalke/datasets/econbiz62k.tsv"
    else:
        p = "/data22/ivagliano/Reuters/rcv1.tsv"

    return p


path = set_path(dataset)

if dataset == "dblp" or dataset == "acm" or dataset == "swp" or dataset == "mpd":
    if dataset != "swp" and dataset != "mpd":
        print("Loading {} dataset".format(dataset.upper()))
        papers = papers_from_files(path, dataset, n_jobs=1)
    elif dataset == "swp":
        print("Loading SWP dataset")
        papers = load(path)
    else:
        print("Loading MPD dataset")
        # actually not papers but playlists
        papers = playlists_from_slices(path, n_jobs=4)

    years, citations, set_cnts = generate_years_citations_set_cnts(papers, dataset)

    if dataset != "mpd":
        # only papers from min_year
        years = from_to_key(years, min_year)
        years = collections.OrderedDict(sorted(years.items()))
        l = list(years.keys())
        print("First year {}, last year {}".format(l[0], l[-1]))
        cnt = 0

        for key, value in years.items():
            cnt += value
            if cnt / len(papers) >= 0.9:
                print("90:10 ratio at year {}".format(key))
                break

        print("Plotting paper distribution by year on file")
        plot(years, dataset, "Year", "Papers")

    if dataset == "acm" or dataset == "swp" or dataset == "mpd":
        if dataset == "acm":
            text = "citations"
        elif dataset == "swp":
            text = "labels"
        else:
            text = "tracks"
        print("Generating {} distribution".format(text))
        citations = paper_by_n_citations(citations)

    print("Unpacking {} data...".format(dataset))
    if dataset == "acm" or dataset == "dblp":
        bags_of_papers, ids, side_info = unpack_papers(papers)
    elif dataset == "mpd":
        # not bags_of_papers but bugs_of_tracks
        bags_of_papers, ids, side_info = unpack_playlists(papers)
    else:
        bags_of_papers, ids, side_info = unpack_papers_fiv(papers)
    bags = Bags(bags_of_papers, ids, side_info)

else:
    print("Loading {}".format(path))
    df = pd.read_csv(path, sep="\t", dtype=str, error_bad_lines=False)
    # replace nan with empty string
    df = df.replace(np.nan, "", regex=True)

    citations = generate_citations(df)
    print("Generating {} distribution"
          .format("citations" if dataset == "pubmed" else "occurrences"))
    citations = paper_by_n_citations(citations)

    set_cnts = set_count(df)

    print("Unpacking {} data...".format(dataset))
    bags = Bags.load_tabcomma_format(path, unique=True)

# only papers with min min_x_cit and max max_x_cit citations
citations = from_to_key(citations, min_x_cit, max_x_cit)
citations = collections.OrderedDict(sorted(citations.items()))

if dataset == "pubmed" or dataset == "acm" or dataset == "dblp":
    x_dim = "Citations"
else:
    x_dim = "Occurrences"
if dataset == "mpd":
    y_dim = "Tracks"
elif dataset == "swp" or dataset == "rcv" or dataset == "econbiz":
    y_dim = 'Labels'
else:
    y_dim = 'Papers'

print("Plotting {} distribution by number of {} on file"
      .format("papers'" if x_dim == "Citations" else "labels'", x_dim.lower()))
# show the y-value for the bar at x=mark_x_cit in the plot
plot(citations, dataset, x_dim, y_dim, mark_x_cit)

print("Generating reference/label/track distribution")
set_cnts = paper_by_n_citations(set_cnts)
set_cnts = from_to_key(set_cnts, min_x_set, max_x_set)
set_cnts = collections.OrderedDict(sorted(set_cnts.items()))

if dataset == "pubmed" or dataset == "acm" or dataset == "dblp":
    x_dim = "References"
elif dataset == "mpd":
    x_dim = "Tracks"
else:
    x_dim = "Labels"

print("Plotting papers' distribution by number of their {} on file".format(x_dim.lower()))
y_dim = "Papers" if dataset != "mpd" else "Playlists"
# show the y-value for the bar at x=mark_x_set in the plot
plot(set_cnts, dataset, x_dim, y_dim, mark_x_set)

bags = bags.build_vocab(apply=True)

csr = bags.tocsr()
print("N ratings:", csr.sum())

column_sums = csr.sum(0).flatten()
row_sums = csr.sum(1).flatten()

print(column_sums.shape)
print(row_sums.shape)

FMT = "N={}, Min={}, Max={} Median={}, Mean={}, Std={}"

print("Items per document")
print(FMT.format(*compute_stats(row_sums)))
print("Documents per item")
print(FMT.format(*compute_stats(column_sums)))
