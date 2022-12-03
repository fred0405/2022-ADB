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
Make sure the `python` command refers to Python version 3.
* run with interactive input
  * `python src/main.py`
  * then type the instructions to be executed and press enter

* run with a single input file
    * `python src/main.py < ./inputs/test1.txt > ./outputs/test1.txt_out`

* run a batch of input files
    * run the batch script `./runit.sh ./inputs ./outputs`
    * it will run the test files `test1 ~ test21` in the `inputs` directory
    * output files will be generated in the `outputs` directory

* unzip and run reprounzip file
    * unzip: `./reprounzip directory setup repro_file.rpz ./your_directory_name`
    * run: `./reprounzip directory run ./your_directory_name < text_input_file_name`
    * it will run the program with the input file `text_input_file_name`
    * the logs and dump results are printed to the standard output
