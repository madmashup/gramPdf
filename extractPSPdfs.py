
#http://www.ceo.kerala.gov.in/detailedResultsGE2016.html
#https://www.binpress.com/tutorial/manipulating-pdfs-with-python/167
import os
import subprocess
import re
import pandas as pd
import numpy as np
import csv

from PyPDF2 import PdfFileWriter, PdfFileReader


DEBUG = True

# Valid choices: PB or LAC
PARSE_TYPE = "PB"


TAB_BASE_CMD = "java -jar tabula-0.9.2.jar "
AREA_OPT = "--area"
PAGE_OPT = "--page"


# ----------------- Polling Booth PDF Areas -----------------------
# Tabula areas for parsing polling booth pdf files
PB_AREAS = {}
PB_AREAS["2011"] = {"t1p1": "40,22,90,548", # First page headers to parse District and LAC
                    "t1pn": "94.5,10.789,802.879,562.164", # Areas for normal pages from 1 to end
                    }
PB_AREAS["2014"] = {"t1p1": "40,22,90,548", # First page headers to parse District and LAC
                    "t1pn": "94.5,10.789,802.879,562.164", # Areas for normal pages from 1 to end
                    }
PB_AREAS["2017"] = {"t1p1": "51,51,92,340", # First page headers to parse District and LAC
                    "t1pn": "114.917,50.95,783.593,556.734", # Areas for normal pages from 1 to end
                    }

def get_num_pdf_pages(pdf_fn):
    #This funcdtion returns the actual total number of pages in the PDF document
    pdf = PdfFileReader(open(pdf_fn, 'rb'))
    return pdf.getNumPages()


def get_pdf_list(path):
    pdf_list = []
    for fileN in os.listdir(path):
        match = re.findall(r"\w+\.pdf", fileN)
        if match:
            pdf_list.append(os.path.join(path, fileN))
    if len(pdf_list) == 0:
        print("Could not find any PDF files in the directory:", path)
    return pdf_list



def get_dist_lac (pdf, areas):
    # Figure out the district and LAC
    # Run the command and get output
    cmdOut = run_tabula(1, areas["t1p1"], pdf)
    #Break in case the cmd was not successful
    if cmdOut == None:
        return None

    if DEBUG:
        print(cmdOut.encode('latin-1'))

    distName = ""
    lacName = ""
    lacNum = ""

    m1 = re.search(r"DISTRICT.*:-*\s+\d*\s+([A-Za-z]+)", cmdOut)
    if m1:
        distName = m1.group(1)

    m2 = re.search(r"LAC.*:.*\s+(\d{1,3})\s+([a-zA-Z]+)", cmdOut)
    if m2:
        lacNum = m2.group(1)
        lacName = m2.group(2)
    
    return (distName, lacNum, lacName)



def process_pdfs(pdfs, areas, outPath):
    for pdf in pdfs:
        print(pdf)

        dist_lac = get_dist_lac(pdf, areas)
        if dist_lac:
            (dist, lacNum, lacName) = dist_lac

        if DEBUG:
            print(dist, lacNum, lacName)
            
        # Output Csv
        csvName = '_'.join([lacNum, dist, lacName])  + ".csv"
        csvName = os.path.join(outPath, csvName)

        # Get number of pages in the pdf
        num_pages = get_num_pdf_pages(pdf)
        print(num_pages, "actual total pages in PDF")


        # Run tabula to convert pdf to csv
        
        pages = ("1-%d" % (num_pages))

        txt = run_tabula(pages, areas["t1pn"], pdf)
        
        process_text(txt, csvName)

        print()



def process_text(txt, outfile):
    csvTxt = ""
    psNum = 0
    gp = ""
    psDict = {}
    
    gp = ""

    for line in txt.split('\n'):
        lineMatch = False

        if DEBUG:
            print(line.encode("latin-1", "ignore"))


        if re.search('(POLLING STATION NAME)*(NAME OF POLLING STATION)', line): # or not re.search('[a-zA-Z]{2,}', line):
            print("\t\tSkipped Line\n", line, "\n")
            continue


        # Regex for GP 2017 files
        mat0 = re.search(r'"*\t+[CORGPMNCU]{2,5}\s+([a-zA-Z -0-9]+)', line)
        if mat0:            
            lineMatch = True
            gp = mat0.group(1).strip()
            
            if DEBUG:
                print("Match 0: ", mat0.group(0).encode("latin-1", "ignore").decode())


        # Regex for PSAddress + Ward with no GP for 2017 files
        mat05 = re.search(r'^(\d+)\t+([a-zA-Z0-9 -_,].+)\t+([A-Za-z0-9].*)', line)
        if mat05:            
            lineMatch = True
            psNum = int(mat05.group(1))
            psDict[psNum] = {}
            psDict[psNum]["PS #"] = psNum

            psadd = mat05.group(2).strip().replace('"', '')
            psadd = re.sub(r'\s+', ' ', psadd)
            psDict[psNum]["PS Address"] = psadd

            psDict[psNum]["Ward"] = mat05.group(3).strip()
            if gp != "":
                psDict[psNum]["GP/MN"] = gp
            
            if DEBUG:
                print("Match 05: ", mat05.group(0).encode("latin-1", "ignore").decode())
                print(str(psDict[psNum]).encode("latin-1", "ignore").decode())

        
        # Regex for PSNum + PSAddress + GP + Ward for 2011,2014 files
        mat1 = re.search(r'^(\d+)(.*)[GPMNC]{2}\s+([a-zA-Z -0-9]+)(.*)', line)
        if mat1:            
            lineMatch = True
            psNum = int(mat1.group(1))
            psDict[psNum] = {}
            psDict[psNum]["PS #"] = psNum

            psadd = mat1.group(2).strip().replace('"', '')
            psadd = re.sub(r'\s+', ' ', psadd)
            psDict[psNum]["PS Address"] = psadd

            psDict[psNum]["Ward"] = mat1.group(4).strip()
            psDict[psNum]["GP/MN"] = mat1.group(3).strip()
            
            if DEBUG:
                print("Match 1: ", mat1.group(0).encode("latin-1", "ignore").decode())
                print(str(psDict[psNum]).encode("latin-1", "ignore").decode())

        # Regex for Ward for 2011,2014 files
        mat15 = re.search(r'^\t+(Ward.*)', line)
        if mat15 and not lineMatch:
            lineMatch = True
            ward = mat15.group(1).replace('\t', ' ')
            ward = re.sub(r'\s+', ' ', ward)
            ward = ward.strip()
            if DEBUG:
                print(ward.encode('latin-1', 'ignore').decode())

            if psDict[psNum]["Ward"] != "":
                psDict[psNum]["Ward"] = psDict[psNum]["Ward"] + " "

            psDict[psNum]["Ward"] = psDict[psNum]["Ward"] + ward
            
            if DEBUG:
                print("Match 1.5: ", mat15.group(1).encode("latin-1", "ignore").decode())
                print(str(psDict[psNum]).encode("latin-1", "ignore").decode())

        # Regex for hanging PSAddress lines for 2011,2014 files
        mat2 = re.search(r'^[^\t]*\t{1}(?!Ward)([a-zA-Z0-9 -][a-zA-Z0-9 -_,]+)\t+([a-zA-Z0-9 -_,]*)', line)
        if mat2 and not lineMatch:
            lineMatch = True
            psadd = mat2.group(1).replace('\t', ' ').replace('"', '')
            psadd = re.sub(r'\s+', ' ', psadd)
            
            ward = mat2.group(2).replace('\t', ' ')
            ward = re.sub(r'\s+', ' ', ward)
            ward = ward.strip()


            if psDict[psNum]["PS Address"] != "":
                psDict[psNum]["PS Address"] = psDict[psNum]["PS Address"] + " "
                
            if psDict[psNum]["Ward"] != "":
                psDict[psNum]["Ward"] = psDict[psNum]["Ward"] + " "

            psDict[psNum]["PS Address"] = psDict[psNum]["PS Address"] + psadd
            psDict[psNum]["Ward"] = psDict[psNum]["Ward"] + ward
            
            if DEBUG:
                print("Match 2: ", mat2.group(0).encode("latin-1", "ignore").decode())
                print(str(psDict[psNum]).encode("latin-1", "ignore").decode())

        # Regex for PSAddress+Ward for 2011,2014 files
        mat25 = re.search(r'^([a-zA-Z0-9 -][a-zA-Z0-9 -_,]+)\t+([a-zA-Z0-9 -_,]+)', line)
        if mat25 and not lineMatch:
            lineMatch = True
            psadd = mat25.group(1).replace('\t', ' ').replace('"', '')
            psadd = re.sub(r'\s+', ' ', psadd)
            
            ward = mat25.group(2).replace('\t', ' ')
            ward = re.sub(r'\s+', ' ', ward)
            ward = ward.strip()


            if psDict[psNum]["PS Address"] != "":
                psDict[psNum]["PS Address"] = psDict[psNum]["PS Address"] + " "
                
            if psDict[psNum]["Ward"] != "":
                psDict[psNum]["Ward"] = psDict[psNum]["Ward"] + " "

            psDict[psNum]["PS Address"] = psDict[psNum]["PS Address"] + psadd
            psDict[psNum]["Ward"] = psDict[psNum]["Ward"] + ward
            
            if DEBUG:
                print("Match 2.5: ", mat25.group(0).encode("latin-1", "ignore").decode())
                print(str(psDict[psNum]).encode("latin-1", "ignore").decode())


        # b'""\t\tTo 360, 367 to 409\t\t'
        mat3 = re.search(r'\t+(.*)', line)
        if mat3 and not lineMatch:
            lineMatch = True
            ward = mat3.group(1).replace('\t', ' ')
            ward = re.sub(r'\s+', ' ', ward)
            ward = ward.strip()
            if DEBUG:
                print(ward.encode('latin-1', 'ignore').decode())

            if not psNum in psDict.keys():
                print("THIS LINE IS WEIRD:\n", line, "\n")
                continue

            if psDict[psNum]["Ward"] != "":
                psDict[psNum]["Ward"] = psDict[psNum]["Ward"] + " "

            psDict[psNum]["Ward"] = psDict[psNum]["Ward"] + ward
            
            if DEBUG:
                print("Match 3: ", mat3.group(1).encode("latin-1", "ignore").decode())
                print(str(psDict[psNum]).encode("latin-1", "ignore").decode())

        # # Catchall
        # mat4 = re.search(r'\t(.*)', line)
        # if mat4 and not lineMatch:
        #     lineMatch = True
        #     ward = mat4.group(1).replace('\t', ' ')
        #     ward = re.sub(r'\s+', ' ', ward)
        #     ward = ward.strip()
        #     if DEBUG:
        #         print(ward.encode('latin-1', 'ignore').decode())

        #     if psDict[psNum]["Ward"] != "":
        #         psDict[psNum]["Ward"] = psDict[psNum]["Ward"] + " "

        #     psDict[psNum]["Ward"] = psDict[psNum]["Ward"] + ward
            
        #     if DEBUG:
        #         print("Match 4: ", mat4.group(1).encode("latin-1", "ignore").decode())
        #         print(str(psDict[psNum]).encode("latin-1", "ignore").decode())

        if not lineMatch:
            if DEBUG:
                print("\nNO MATCH\n")

    with open(outfile, 'w', newline='') as outf:
        fieldNames = ["PS #", "GP/MN", "PS Address", "Ward"]
        writer = csv.DictWriter(outf, fieldnames = fieldNames)
        writer.writeheader()

        keyList = list(psDict.keys())
        keyList.sort()
        for k in keyList:
            writer.writerow(psDict[k])



# def process_csv(csvName):
#     print(csvName)
    
#     #Read in the CSV. We need to specify the col names because the CSV is of variable length
#     colnames = ["PS #", "PS Address", "GPAndWard1", "GPAndWard2", "GPAndWard3"]
#     data = pd.read_csv(csvName, names=colnames, header=None, delimiter="\t", encoding = "ISO-8859-1") # Tab delimited

#     # Concatenate the GP and Ward columns
#     data["GPAndWard"] =  data[["GPAndWard1", "GPAndWard2", "GPAndWard3"]].fillna('').apply(lambda x: ' '.join(x), axis=1)

#     # Since we have concatenated, drop the individual columns
#     data.drop(["GPAndWard1", "GPAndWard2", "GPAndWard3"], axis=1, inplace=True)

#     # Forward fill the PS Number column so that the blank cells are filled with the previous number
#     data["PS #"].fillna(method='ffill', axis=0, inplace=True)

#     # Now drop the columns that have nonnumeric values under PS #
#     # data = data.loc[data["PS #"].str.isnumeric()].reset_index(drop=True)

#     # Replace NaNs with empty strings, otherwise it casuses problems with groupby
#     data.fillna("", inplace=True)

#     # Groupby PS # (PS Numbers) and join the rows for each PS Number with space as delimeter
#     psAddress = data.groupby("PS #", sort=False)['PS Address'].apply(lambda x: ' '.join(x)) 
#     gpAndWard = data.groupby("PS #", sort=False)['GPAndWard'].apply(lambda x: ' '.join(x))

#     # Now concatenate the new columns
#     data = pd.concat([psAddress, gpAndWard], axis=1).reset_index()

#     # There is some mismatch in columns, so we want to consolidate everything and then parse with regexes
#     data['PS'] = data["PS Address"] + data["GPAndWard"]

#     # Split the GP and Ward coverage columnsdata["GP/MN"] = data["GPAndWard"].str.split('  ').str.get(0)
#     data["PS Address"] = data["PS"].str.extract(r'(.+)[GPMN]{2} .*', expand=False)
#     data["GP/MN"] = data["PS"].str.extract(r'[GPMN]{2} (\w+)\s+', expand=False)
#     data["Ward"] = data["PS"].str.extract(r'(Ward .*)', expand=False)

#     # Drop the consolidated column
#     data.drop(["PS", "GPAndWard"], inplace=True, axis=1)

#     # Write the CSV to disk
#     data.to_csv(csvName, index=False)


def run_tabula(pageRange, area, pdf, outFile=None):
    cmd = " ".join([TAB_BASE_CMD, "--pages", str(pageRange), "--area", area, "--format TSV", pdf])
    
    if outFile:
        cmd = " ".join([cmd, "--outfile", outFile])
    
    if DEBUG:
        print(cmd)

    cmdOut = None

    #Run the command and process output
    try:
        cmdOut = subprocess.check_output(cmd, universal_newlines=True)
    except BaseException as e:
        print("\t**=> Exception while running subprocess for file %s\nCommand:%s\nError:%s" % (pdf, cmd, str(e)))
        return None

    return cmdOut



def main():
    global DEBUG
    DEBUG = False

    pdfFilesPath = "pollingStations2017"
    pdfs = get_pdf_list(pdfFilesPath)

    # pdfs = ["pollingStations2017/AC027.pdf"]
    process_pdfs(pdfs[86:], PB_AREAS[pdfFilesPath[-4:]], pdfFilesPath);
    

if __name__=='__main__':
    main()
