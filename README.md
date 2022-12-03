# Documentation and Code Structure - RepCRec

This project is a course project of Advanced Database System (CSCI-GA.2434-001) in New York University, Fall 2022, taught by Professor Dennis Shaha.

We implement a tiny distributed database and complete multi-version concurrency control, deadlock detection, replication, and failure recovery.

## Team Members
 
 - Shang-Chuan Liu (sl9413@nyu.edu)
 - Siwei Liu (sl9386@nyu.edu)


## Programming Language

Python 3

## Design Diagram

![](Designgraph.png)

## How To Run

* run test1 ~ test21 in the `inputs` directory
    * use this command: `./runit.sh`
    * output files will be generated in the `outputs` directory

* run certain test
    * use this command: `python main.py < ./inputs/test1 > ./outputs/test1.txt_out`
    * output file `test1.txt_out` will be generated in the `outputs` directory

* unzip and run reprounzip file
    * use this command to unzip: `./reprounzip directory setup RepCRec.rpz ~/yourDesiredDirectoryName`
    * use this command to run: `./reprounzip directory run ~/yourDesiredDirectoryName`
    * it will run test1 ~ test24 in the `inputs` directory
    * output files will be generated in the `outputs` directory
