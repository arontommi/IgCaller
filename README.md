# IgCaller

#### Reconstructing the IG gene rearrangements and oncogenic translocations from WGS

IgCaller is a python program designed to fully characterize the immunoglobulin gene rearrangements and oncogenic translocations in lymphoid neoplasms from whole-genome sequencing data.

![alt text](https://github.com/ferrannadeu/IgCaller/blob/master/IgCaller_workflow.jpg)

### Requirements

IgCaller is based on python3 and requires the following modules: subprocess, sys, os, itertools, operator, collections, statistics, argparse (v1.1), regex (v2.5.29 and v2.5.30), numpy (1.16.2 and v1.16.3), and scipy (v1.2.1 and v1.3.0). Although providing the versions of the previous modules tested, we are not aware about any specific version requirement for running IgCaller.

The only required non-python program is [samtools](http://www.htslib.org) (version 1.6 and 1.9 have been tested).

### Running IgCaller

#### Mandatory arguments:
*	inputsFolder (-I): path to the folder containing the supplied IgCaller reference files.
*	genomeVersion (-V): version of the reference human genome used when aligning the WGS data (hg19 or hg38).
*	chromosomeAnnotation (-C): chromosome annotation [ensembl = without 'chr' (i.e. 1); ucsc = with 'chr' (i.e. chr1)].
*	bamT (-T): path to tumor BAM file.
*	bamN (-N): path to normal BAM file, if available.
*	refGenome (-R): path to reference genome FASTA file (not mandatory, but recommended, when specifying a normal BAM file. Mandatory when bamN not specified).

#### Optional arguments:
*	pathToSamtools (-ptsam): path to the directory where samtools is installed. There is no need to specify it if samtools is found in “PATH” (default = ‘empty’, assuming it is in “PATH”).
*	outputPath (-o): path to the directory where the output should be stored. Inside the defined directory IgCaller will automatically create a folder named “tumorSample”_IgCaller where output files will be saved (default, current working directory).
*	mappingQuality (-mq): mapping quality cut off to filter out reads (default = 0).
*	baseQuality (-bq): base quality cut off to consider a position in samtools mpileup when reconstructing both normal and tumor sequences (default = 13).
*	minDepth (-d): depth cut off to consider a position (default = 1).
*	minAltDepth (-ad): alternate depth cut off to consider a potential alternate nucleotide (default = 1)
*	vafCutoffNormal (-vafN): minimum variant allele frequency (VAF) to consider a nucleotide when reconstructing the germ line sequence using the supplied normal BAM file (if available) (default = 0.2).
*	vafCutoff (-vaf): minimum VAF to consider a nucleotide when reconstructing the tumor sequence (default = 0.1). Try to increase this value if only unproductive rearrangements are found due to stop codons. We have observed that relatively high coverage WGS (i.e. 100x) might carry many variants (likely sequencing artifacts) at VAFs around 10-20%.
*	tumorPurity (-p): purity of the tumor sample (i.e. tumor cell content) (default = 1). It is used to adjust the VAF of the mutations found in the tumor BAM file before filtering them using the vafCutoff, to adjust the score of each rearrangement, and to adjust the reduction of read depth in the CSR analysis.
*	minNumberReadsTumorOncoIg (-mntonco): Minimum score supporting an IG rearrangement in order to be annotated (default = 4).
*	minNumberReadsTumorOncoIgPass (-mntoncoPass): Minimum score supporting an IG rearrangement in the tumor sample in order to be considered as high confidence (default = 10).
*	maxNumberReadsNormalOncoIg (-mnnonco): Maximum number of reads supporting an IG rearrangement in the normal sample in order to be considered as high confidence (default = 2).
*	numThreads (-@): Maximum number of threads to be used by samtools (default = 1).


#### Basic command line to execute IgCaller:
```
python3 path/to/IgCaller/IgCaller_v1.py -I path/to/IgCaller/IgCaller_reference_files/ -V hg19 -C ensembl -T path/to/bams/tumor.bam -N path/to/bams/normal.bam -R path/to/reference/genome_hg19.fa -o path/to/IgCaller/outputs/
```

#### Tested on:
IgCaller was tested on a MacBook Pro (macOS Mojave), Ubuntu (16.04 and 18.04), and MareNostrum 4 (Barcelona Supercomputing Center, SUSE Linux Enterpirse Server 12 SP2 with python/3.6.1).

#### Running time:
IgCaller only requires 1 CPU, and it usually takes <2-5 minutes to characterize the complete IG gene of one tumor sample. 

### Outputs

IgCaller returns a set of tab-separated files:

*	tumor_sample_output_filtered.tsv: High confidence rearrangements passing the defined filters.
*	tumor_sample_output_IGH.tsv: File containing all IGH rearrangements.
*	tumor_sample_output_IGK.tsv: File containing all IGK rearrangements.
*	tumor_sample_output_IGL.tsv: File containing all IGL rearrangements.
*	tumor_sample_output_class_switch.tsv: File containing all CSR rearrangements.
*	tumor_sample_output_oncogenic_IG_rearrangements.tsv: File containing all oncogenic IG rearrangements (translocations, deletions, inversions, and gains) identified genome-wide.

### Bugs, comments and improvements

Bugs, comments and improvements can be send to *nadeu@clinic.cat*. They will be very much appreciated!

