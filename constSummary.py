import os
import re
import numpy as np
import pandas as pd


def get_file_list(path, file_extn):
    pdf_list = []
    for fn in os.listdir(path):
        match = re.findall("\s*\d+\\."+file_extn, fn)
        if match:
            pdf_list.append(os.path.join(path,fn))
    if len(pdf_list) == 0:
        print ("Could not find any \s files in the directory:".format(file_extn), path)
    return pdf_list


def wrangle_results(results_fn):
    # Prepare the 2016 Results file
    df = pd.read_csv(results_fn)
    df.drop(df.columns[0], axis=1, inplace=True)

    newcols1 = ['Constituency', 'District', 'Candidate', 'Party', 'Votes']
    part1 = df.iloc[:,0:5]
    part1.columns = newcols1
    newcols2 = newcols1[2:5]
    part2 = df.iloc[:,5:8]
    part2.columns = newcols2
    part3 = df.iloc[:,8:11]
    part3.columns = newcols2

    comp = pd.concat([part1, part2, part3], axis=0)
    comp.reset_index(inplace=True)
    comp.drop('index', axis=1, inplace=True)
    comp['Alliance'] = pd.DataFrame(['UDF']*140 + ['LDF']*140 + ['NDA']*140)
    comp['Constituency'] = pd.concat([comp.iloc[0:140,1]] * 3).tolist()
    comp['District'] = pd.concat([comp.iloc[0:140,2]] * 3).tolist()
    comp['Votes'] = comp['Votes'].apply(pd.to_numeric, errors = 'coerce')

    return comp




def get_boothwise_results(fileList, constiResults):
    finalFrame = pd.DataFrame()
    # Now go through each constituency file and look up the candidate names from the results file
    for fn in fileList:
        #Read in the csv file
        const1 = pd.read_csv(fn, skiprows=[0,1])
        # We're note interested in the last couple of lines in the csv that list the candidates
        # So let's delete everything after the Totals line
        total_line_idx = const1[const1[const1.columns[0]] == "Total Votes Polled"].index[0]
        last_idx = const1.shape[0]
        # Deletes everything after the Totals Votes Polled line
        const1.drop(const1.index[range(total_line_idx + 1,last_idx)], axis=0, inplace=True)

        # Make sure that our numbers are of type numeric, otherwise it'll cause problems
        const1[const1.columns[1:22]] = const1[const1.columns[1:22]].apply(pd.to_numeric, errors='coerce')

        # Now transpose the data so that the candidates are the row indexes and polling
        # stations are the columns. The "Total" column will contain the results that
        # we can compare in the other results file
        c1 = const1.transpose()
        c1.columns = c1.iloc[0,:]
        c1.drop(c1.index[0], axis=0, inplace=True)
        c1.columns.name=None
        c1 = c1.apply(pd.to_numeric, errors = 'coerce')

        results = pd.merge(c1, constiResults, left_on="Total Votes Polled", right_on='Votes', how='inner', suffixes=('_x', '')).dropna(axis=1)
        finalFrame = pd.concat([finalFrame, results], axis = 0)
        finalFrame.reset_index(inplace=True)
        finalFrame.drop(['index'], axis=1, inplace=True)

    return finalFrame

def main():
    filesPath = 'ge2016/csvs/'
    csvs = get_file_list(filesPath, 'csv')
    resultsFile = "lacResults2016.csv"
    constiResults = wrangle_results(resultsFile)
    boothwise_results = get_boothwise_results(csvs, constiResults)
    boothwise_results.transpose().to_csv('ge2016boothwise_results.csv')

if __name__=='__main__':
    main()
