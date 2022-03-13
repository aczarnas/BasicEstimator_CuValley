# Basic Generator  

How to use?  

* install required python libraries (`pip install -r requirements.txt`)  
* run with (at least required) parameters:
  * `python basic_generator.py --path-to-data=<path to input data dir with files packed by gzip> --path-to-test-file=<path to csv file with proper temperatures> [--output-file-name=<optional parameter - name of file to save generated temperatures with timestamps>]`
* if all inputs are correct, as a result application will show mean squared error for generated data based on test file