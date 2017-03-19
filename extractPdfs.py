#http://www.ceo.kerala.gov.in/detailedResultsGE2016.html
#https://www.binpress.com/tutorial/manipulating-pdfs-with-python/167
import os
import subprocess
import re
from PyPDF2 import PdfFileWriter, PdfFileReader

csv_heading = ''',Candidate
,A,B,C,D,E,F,G,H,I,J,K,L,M,N,O,P,Q,R,S,T,U
Serial No of Polling Station,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,Total # of Valid Votes,# of Rejected,Total,# of Tend Vote
'''


csv_last_rows=[]
csv_last_rows.append("Total No of Votes recorded at Polling")
csv_last_rows.append("No.of Votes recorded on postal ballot papers(To be filled in the case of election from assembly constituency)")
csv_last_rows.append("Total Votes Polled")


tab_base_cmd = "java -jar tabula-0.9.1.jar --no-spreadsheet"
area_opt = "-a"
page_opt = "-p"


# Areas for the tabula command to extract the relevant data
tabulaAreas = { "t1p1": "308.342,12.102,499.872,829.788", # First page is slightly truncated
                "t1p2": "67.351,11.05,487.244,829.788", # Normal pages between 2 to end-1
                "t1l1": "67.351,58.563,329.389,828.735", # 1st half of last page
                "t1l2": "355.699,11.05,385.165,838.207" # last half of last page
              }

# Holds the areas and text for verifying the page
checkPageAreas = { "t1p1": ["95.239,340.439,115.234,501.451", "FINAL RESULT SHEET"],
                   "t1p2": ["71.034,14.207,129.967,58.406", "\d+"],
                   "t1l1": ["71.034,14.207,129.967,58.406", "Total No"],
                 }

# Area for checking the number of pages
numPagesArea = "507.765,29.992,528.812,146.805"

def get_num_pdf_pages(pdf_fn):
    #This funcdtion returns the actual total number of pages in the PDF document
    pdf = PdfFileReader(open(pdf_fn, 'rb'))
    return pdf.getNumPages()


def get_num_of_data_pages(pdf_fn):
    # This function returns the number of pages that contain parsable data. this
    # number is printed on each page of the document, with the line "Total
    # Number Of Pages: "
    cmdOut = run_tabula(1, numPagesArea, pdf_fn)
    if cmdOut == None:
        print("Error: Could not get the number of pages in file!")
        return None

    match = re.findall("\d+", cmdOut)
    if match:
        numDataPages = int(match[0])
    else:
        return None

    return numDataPages

def verify_totals_page(pg, pdf):
    cmdOut = run_tabula(pg, checkPageAreas['t1l1'][0], pdf)
    if cmdOut == None:
        print("Error: Could not verify if the page is indeed a totals page!")
        return None

    cmdOut = cmdOut.replace('\n',' ')
    match = re.findall(checkPageAreas['t1l1'][1], cmdOut)
    if len(match) > 0:
        return True
    else:
        return False


def get_pdf_list(path):
    pdf_list = []
    for fn in os.listdir(path):
        match = re.findall("\d+\\.pdf", fn)
        if match:
            pdf_list.append(os.path.join(path,fn))
    if len(pdf_list) == 0:
        print ("Could not find any PDF files in the directory:",path)
    return pdf_list


def process_pdfs(pdfs, areas, outPath):
    for pdf in pdfs:
        print(pdf)
        # Output Csv
        csvName = pdf.split('.')[0]+".csv"

        #Write the header first
        out_fh = open(csvName, "w")
        out_fh.write(csv_heading)

        extractOut = extract_manager(pdf, areas)
        if extractOut == None:
            print("Skipping PDF ", pdf)
            continue

        # Finally, write the output to the csv file
        out_fh.write(extractOut)



def extract_manager(pdf, areas):
        #Make sure that our conversion command didn't cause an exception; if they did, skip this pdf
        conv_error = False

        #out captures the complete output
        out = ""

        # Get total number of pages
        numDataPages = get_num_of_data_pages(pdf)
        print(numDataPages,"pages of tables in PDF")

        # Get the total number of actual pages as well
        numTotalPages = get_num_pdf_pages(pdf)
        print(numTotalPages,"actual total pages in PDF")


        # ** NORMAL PAGES **
        # Go through a loop for each page in the pdf and the corresponding area
        for (pg, area) in zip([1, "2-" + str(numDataPages - 1)], [areas['t1p1'], areas['t1p2']]):
            #Run the command and get output
            cmdOut = run_tabula(pg, area, pdf)
            #Break in case the cmd was not successful
            if cmdOut == None:
                conv_error = True
                break

            #Append the output to the out variable if successful
            out += cmdOut

        #Skip PDF if there was an error
        if conv_error:
            return None

        # ** LAST PAGE - PART 1 **
        # Processing the last/totals page separately since it has multiple parts
        # First, we need to verify that it is indeed the totals page and the
        # "Total Number Of Pages" line on each page in the pdf is right.
        # If it's wrong, the totals page will be off.
        # If this is not the totals page, then continue using the area for the
        # normal pages until we hit the results page, or end of file
        for pg in range(numDataPages, numTotalPages+1):
            areasKey = 't1p2'
            isTotalsPage = False

            # Make sure that it is indeed the totals page
            if verify_totals_page(pg, pdf) == True:
                isTotalsPage = True
                areasKey = 't1l1'
                print("Page", pg, "is a totals page")

            cmdOut = run_tabula(pg, areas[areasKey], pdf)
            # Return None if this command didn't work
            if cmdOut == None:
                return None

            if isTotalsPage == True:
                # Now append the previous output manually by splitting the lines and
                # adding the row names, otherwise it becomes a mess
                # The last page looks like this
                #   Total No of Votes recorded at Polling 1107 11207 51226 56922 602 88 768 2537 74 254 91 268 454 192 90 698 0 0 0 0 989 126578 0 126578 1
                #   No.of Votes recorded on postal ballot papers
                #   Total Votes Polled 1107 11207 51226 56922 602 88 768 2537 74 254 91 268 454 192 90 698 0 0 0 0 989
                #
                # Also, if the 2nd row is empty, there is a mismatch in the rownames and the
                # values to be put there (3 vs 2). So we need to insert a 0 in the data
                # values list, if the lastPageData is 1 less than the csv_last_rows.

                i = 0

                totalsPageData = cmdOut.strip().split("\n")
                if len(totalsPageData) == len(csv_last_rows) - 1:
                    totalsPageData.insert(1,"0")
                # Go through the data lines, append them with the row names, and add them
                # to the output
                # print (totalsPageData, csv_last_rows)
                for line in totalsPageData:
                    out += csv_last_rows[i] + "," + line + "\n"
                    i += 1

                break

            else:
                #Append the output to the out variable if successful
                out += cmdOut


        # TODO: See if parsing the candidate key makes sense anymore
        # # ** LAST PAGE - PART 2 **
        # #Now capture the candidate names line which is the last line on the last page
        # #There are 2 cases for the 2 types of files. The operations are the same,
        # #so we'll just put a loop here
        # for ind in range(0,0):
        #     key = "area" + str(ind)
        #     if key in areas:
        #         cmdlast2out = run_tabula(numDataPages, areas[key], pdf)
        #         #Skip PDF if there is an error in conversion
        #         if cmdlast2out == None:
        #             print("Skipping PDF ", pdf)
        #             break
        #
        #         #Append final line to the out variable
        #         out += "\n" + "," + ",".join(cmdlast2out.replace("\"","").split(","))


        return out



def run_tabula(pageRange, area, pdf):
    cmd = " ".join([tab_base_cmd, "-p", str(pageRange), "-a", area, pdf])
    cmdOut = None

    #Run the command and process output
    try:
        cmdOut = subprocess.check_output(cmd, universal_newlines=True)
    except BaseException as e:
        print("\t**=> Exception while running subprocess\nCommand:{}\nError:{}".format(pdf,cmd,str(e)))
        return None

    return cmdOut



def main():
    pdfFilesPath = "ge2014"
    pdfs = get_pdf_list(pdfFilesPath)
#    pdfs = [os.path.join("074.pdf")]
    process_pdfs(pdfs, tabulaAreas, pdfFilesPath);


if __name__=='__main__':
    main()
