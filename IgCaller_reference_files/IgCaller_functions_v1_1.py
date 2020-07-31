# Modules
import subprocess
import os
import regex as re
import numpy as np
import itertools
import operator
from collections import Counter
from scipy import stats
from statistics import mean

# dicts
complement = {'A': 'T', 'C': 'G', 'G': 'C', 'T': 'A', 'N': 'N', 'R': 'R', '[': ']', ']': '[', '(': ')', ')': '('}

tripletsToAA = {'ATA':'I', 'ATC':'I', 'ATT':'I', 'ATG':'M',
				'ACA':'T', 'ACC':'T', 'ACG':'T', 'ACT':'T', 
				'AAC':'N', 'AAT':'N', 'AAA':'K', 'AAG':'K', 
				'AGC':'S', 'AGT':'S', 'AGA':'R', 'AGG':'R',             
				'CTA':'L', 'CTC':'L', 'CTG':'L', 'CTT':'L', 
				'CCA':'P', 'CCC':'P', 'CCG':'P', 'CCT':'P', 
				'CAC':'H', 'CAT':'H', 'CAA':'Q', 'CAG':'Q', 
				'CGA':'R', 'CGC':'R', 'CGG':'R', 'CGT':'R', 
				'GTA':'V', 'GTC':'V', 'GTG':'V', 'GTT':'V', 
				'GCA':'A', 'GCC':'A', 'GCG':'A', 'GCT':'A', 
				'GAC':'D', 'GAT':'D', 'GAA':'E', 'GAG':'E', 
				'GGA':'G', 'GGC':'G', 'GGG':'G', 'GGT':'G', 
				'TCA':'S', 'TCC':'S', 'TCG':'S', 'TCT':'S', 
				'TTC':'F', 'TTT':'F', 'TTA':'L', 'TTG':'L', 
				'TAC':'Y', 'TAT':'Y', 'TAA':'*', 'TAG':'*', 
				'TGC':'C', 'TGT':'C', 'TGA':'*', 'TGG':'W'
				}  

# functions
def smithwaterman(x, y, match_score=5, mismatch_cost=4, gap_cost=8):
    # scoring matrix
	M = np.zeros((len(x) + 1, len(y) + 1), np.int) # +1 because of the zero column and zero row
	for i, j in itertools.product(range(1, M.shape[0]), range(1, M.shape[1])): 
		match = M[i - 1, j - 1] + (match_score if x[i - 1] == y[j - 1] else - mismatch_cost)
		delete = M[i - 1, j] - gap_cost
		insert = M[i, j - 1] - gap_cost
		M[i, j] = max(match, delete, insert, 0)
	# Get maximum score
	M_flip = np.flip(np.flip(M, 0), 1)
	i_, j_ = np.unravel_index(M_flip.argmax(), M_flip.shape)
	i, j = np.subtract(M.shape, (i_ + 1, j_ + 1))
	return M[i,j]

def getGeneralInfo(GENE, chrom, genomeVersion, inputsFolder, chrAnnot):
	Dseqs = "NA"
	if GENE == "IGH":
		chromGene = chrom+"14"		
		if genomeVersion == "hg19":
			bedFile = inputsFolder+"/hg19/"+chrAnnot+"/wgEncodeGencodeBasicV19_hg19_IGH_genes_VJ.bed"
			Dseqs = inputsFolder+"/hg19/"+chrAnnot+"/DB_D_genes_seq_wgEncodeGencodeBasicV19_hg19.txt"
		else:
			bedFile = inputsFolder+"/hg38/"+chrAnnot+"/GencodeV29_hg38_IGH_genes_VJ.bed"
			Dseqs = inputsFolder+"/hg38/"+chrAnnot+"/DB_D_genes_seq_GencodeV29_hg38.txt"
	
	elif GENE == "IGL":
		chromGene = chrom+"22"
		if genomeVersion == "hg19": bedFile = inputsFolder+"/hg19/"+chrAnnot+"/wgEncodeGencodeBasicV19_hg19_IGL_genes_VJ.bed"
		else: bedFile = inputsFolder+"/hg38/"+chrAnnot+"/GencodeV29_hg38_IGL_genes_VJ.bed"

	elif GENE == "IGK":
		chromGene = chrom+"2"
		if genomeVersion == "hg19": bedFile = inputsFolder+"/hg19/"+chrAnnot+"/wgEncodeGencodeBasicV19_hg19_IGK_genes_VJ.bed"
		else: bedFile = inputsFolder+"/hg38/"+chrAnnot+"/GencodeV29_hg38_IGK_genes_VJ.bed"
	
	elif GENE == "CSR":
		chromGene = chrom+"14"
		if genomeVersion == "hg19": bedFile = inputsFolder+"/hg19/"+chrAnnot+"/hg19_Huebschmann_et_al_switch_regions.bed"
		else: bedFile = inputsFolder+"/hg38/"+chrAnnot+"/hg38_liftOver_Huebschmann_et_al_switch_regions.bed"
	
	return(chromGene, bedFile, Dseqs)

def flagToCustomBinary (flag):
	binary = format(int(flag), "b")
	binary = ("0"*(12-len(binary)))+binary
	return(binary[::-1])
	
def convertSamToAnnotatedTable(miniSamT, chromGene, GENE):
	
	samfile = open(miniSamT, "r")
	
	store = {}

	for i in samfile:
		
		w = i.rstrip("\n").split("\t")
		
		if w[5] != "*" and w[6] == "=":
			
			sa = []
			for x in (w[11:]): # analyse values after qualities, starting with SA...
				if x.startswith("SA:Z"):
					sa.append(x)
			if len(sa) != 0: # takes values from position 0 to 9th and appends SA... in the 10th
				w = w[:10]+[sa[0]]
			else:
				w = w[:10]+["NA"]
				
			w.append("NA") # temporal NA to add later "split" or "insertSize" on 11th position
			
			
			split1 = re.findall(r'[A-Za-z]|[0-9]+', w[5])
			two1 = [split1[x:x+2] for x in range(0, len(split1),2)]
			split2 = w[10].split(',') # split SA...
			
		
			if GENE != "CSR" and (w[10].startswith("SA:Z") or sum([int(i[0]) for i in two1 if "S" in i]) > 20): # split if SA or S > 20 in cigar
				if abs(int(w[8])) > 10000:  w[11] = "split-insertSize"
				else: w[11] = "split"
				
			elif abs(int(w[8])) > 10000:  # insertSize if insert size > 10000 [ J-V = 70000bp aprox ]
				w[11] = "insertSize"
			
			
			if 	w[11] == "split" or w[11] == "split-insertSize": # add 2 columns
				
				# 1st_pos
				two1 = [split1[x:x+2] for x in range(0, len(split1),2)]
				if len([count for count, item in enumerate(two1) if "S" in item]) == 0:
					firstpos = sum([int(i[0]) for i in two1 if "M" in i or "D" in i]) - 1
				elif min([count for count, item in enumerate(two1) if "M" in item]) < min([count for count, item in enumerate(two1) if "S" in item]):
					firstpos = sum([int(i[0]) for i in two1 if "M" in i or "D" in i]) - 1
				else:
					firstpos = 0
				
				# first PosSplit
				a = int(w[3]) + firstpos  
				w.append(a)
				
				# second PosSplit
				if w[10].startswith("SA:Z") and split2[0].split(':')[2] == chromGene:
					
					split3 = re.findall(r'[A-Za-z]|[0-9]+', split2[3])
					two2 = [split3[x:x+2] for x in range(0, len(split3),2)]
					
					# get if overlapping same base/s at each break point... we substract this overlapping bases on the first break below
					diffMappingBases = sum([int(i[0]) for i in two2 if "M" in i or "D" in i]) - sum([int(i[0]) for i in two1 if "S" in i]) 
					
					if len([count for count, item in enumerate(two2) if "S" in item]) == 0: 
						secpos = sum([int(i[0]) for i in two2 if "M" in i or "D" in i]) - 1 
					elif min([count for count, item in enumerate(two2) if "M" in item]) < min([count for count, item in enumerate(two2) if "S" in item]):
						secpos = sum([int(i[0]) for i in two2 if "M" in i or "D" in i]) - 1 
					else:
						secpos = 0
						
					b = int(split2[1]) + secpos  # second PosSplit
					w.append(b)
					
					# sort (smaller first)
					w[-2:] = min(w[-2:]), max(w[-2:])
					
					if diffMappingBases > 0: 
						
						if int(flagToCustomBinary(w[1])[4]) == 0: strand = "+"
						else: strand = "-"
						strandSA = w[10].split(",")[2]
						
						# reads <- <-  (Inversion1) => sum diffMappingBases at first read soft clipped position
						if ( int(flagToCustomBinary(w[1])[4]) == 0 and strand == "-" and strandSA == "+" ) or ( int(flagToCustomBinary(w[1])[4]) == 1 and strand == "+" and strandSA == "-" ):
							w[-2] = w[-2] + diffMappingBases
						
						else:  # reads -> <- or -> -> => substract diffMappingBases at first read soft clipped position
							w[-2] = w[-2] - diffMappingBases
				
				
				# for reads not in chromGene add NA
				else:
					w.append("NA")
				
				if w[11] == "split": w.extend(["NA"]* 2) # no insertSize info
				

			if w[11] == "insertSize" or w[11] == "split-insertSize": 
				
				if w[11] == "insertSize": w.extend(["NA"]* 2) # no split info
				
				if int(flagToCustomBinary(w[1])[4]) == 0: # positive strand 
					two = [split1[x:x+2] for x in range(0, len(split1),2)]
					converted = sum([int(i[0]) for i in two if  "I" not in i and "S" not in i]) - 1 
					d = int(w[3]) + converted
				else: # negative strand  
					d = int(w[3]) 
				
				if 	int(flagToCustomBinary(w[1])[6]) == 1 and int(flagToCustomBinary(w[1])[4]) == 0 and int(w[8]) > 0: # first in pair and positive strand and insertSize > 0 (97 -> del) (65 -> inv)
					w.append(d)
					w.append("NA")
				elif int(flagToCustomBinary(w[1])[6]) == 0 and int(flagToCustomBinary(w[1])[4]) == 1 and int(w[8]) < 0: # second in pair and negative strand and insertSize < 0 (145 <- del) (177 <- inv)
					w.append("NA")
					w.append(d)
				elif int(flagToCustomBinary(w[1])[6]) == 1 and int(flagToCustomBinary(w[1])[4]) == 1 and int(w[8]) < 0: # first in pair and negative strand and insertSize < 0 (81 <- del)
					w.append("NA")
					w.append(d)
				elif int(flagToCustomBinary(w[1])[6]) == 0 and int(flagToCustomBinary(w[1])[4]) == 0 and int(w[8]) > 0: # second in pair and positive strand and insertSize > 0 (161 -> del)
					w.append(d)
					w.append("NA")
				elif int(flagToCustomBinary(w[1])[6]) == 0 and int(flagToCustomBinary(w[1])[4]) == 0 and int(w[8]) < 0: # second in pair and positive strand and insertSize < 0 (129 -> inv)
					w.append("NA")
					w.append(d)
				elif int(flagToCustomBinary(w[1])[6]) == 1 and int(flagToCustomBinary(w[1])[4]) == 1 and int(w[8]) > 0: # first in pair and negative strand and insertSize > 0 (113 <- inv)
					w.append(d)
					w.append("NA")
				else:
					w.append("NA")
					w.append("NA")
					if w[11] == "insertSize": w[11] = "NA" # if no deletion or inversions considered above, remove info if no split				
			
			if w[11] == "NA":
				w.extend(["NA"]* 4) # if it is neither insertSize nor split we add the five empty columns for it
			
			
			# dict store:
			if w[0] not in store: # w[0] is read name
				if w[11] == "split" or w[11] == "insertSize" or w[11] == "split-insertSize":
					store[w[0]] = w
			
			else:
				if w[11] == "split" or w[11] == "split-insertSize":
					if store[w[0]][11] == "insertSize":
						if store[w[0]][14] != "NA":
							w[14] = store[w[0]][14] 
						else:
							w[15] = store[w[0]][15]
						
						store[w[0]] = w
				
				if (w[11] == "insertSize" and store[w[0]][11] == "insertSize") or (w[11] == "insertSize" and store[w[0]][11] == "split-insertSize"): # or (w[11] == "split-insertSize" and store[w[0]][11] == "split-insertSize"): no pot ser mai split-insertSize and split-insertSize
					if w[14] != "NA":
						store[w[0]][14] = w[14]
					else:
						store[w[0]][15] = w[15]
	
	return(store)
	
def findJandVgenes(annot_table, bedFile, GENE):
	insertsplit = open(annot_table, "r")
	
	JV_list = []

	for i in insertsplit:
		w = i.rstrip("\n").split("\t")
		w.extend(["NA"]* 4) # we add 4 new columns where we will add new information
		for j in range(12,16):
			if w[j] != "NA": 
				VDJ = open(bedFile, "r") # bed file for V/J genes
				for k in VDJ:
					v = k.rstrip("\n").split("\t")
					if GENE == "IGH": # orientation J - V
						if v[3].startswith("IGHJ"):
							window1 = 0
							window2 = 10
						else:
							window1 = 10
							window2 = 0
					elif GENE == "IGK": # orientation J - V
						if v[3].startswith("IGKJ"):
							window1 = 0
							window2 = 10
						else:
							window1 = 10
							window2 = 5 # 5bp added for inversions just after V
					elif GENE == "IGL": # orientation V - J
						if v[3].startswith("IGLJ"):
							window1 = 10
							window2 = 0
						else:
							window1 = 0
							window2 = 10
					else: # class switch
						window1 = 0
						window2 = 0
					
					if int(w[j]) >= int(v[1])-window1 and int(w[j]) <= int(v[2])+window2: # we check in which V or J is the position included, considering the defined windows
						w[j+4] = v[3] # we append the corresponding V or J, 4 positions to the right to our table
						break
				VDJ.close()	

		# We classify reads according to their orientation (flags) and insert size:
		if w[11] == "insertSize" or w[11] == "split-insertSize":
			
			# reads: -> <-
			if int(w[1]) in [97, 161] and int(w[8]) > 0: w.append("Deletion")
			elif int(w[1]) in [145, 81] and int(w[8]) < 0: w.append("Deletion")
			
			# reads -> ->
			elif int(w[1]) == 65 or int(w[1]) == 129: w.append("Inversion2")
		
			# reads <- <-
			elif int(w[1]) == 113 or int(w[1]) == 177: w.append("Inversion1")
			
			# other potential SV not considered:
			else: w.append("NA")
		
		
		else:
			# no information of soft clipped map:
			if w[10] == "NA": w.append("NotComplete") 
			
			else: # split			
				# get strands
				if int(flagToCustomBinary(w[1])[4]) == 0: strand = "+"
				else: strand = "-"
				strandSA = w[10].split(",")[2]
				
				# reads: -> <-
				if strand == "+" and strandSA == "+" and int(w[8]) > 0: w.append("Deletion")
				elif strand == "-" and strandSA == "-" and int(w[8]) < 0: w.append("Deletion")
				
				# reads -> ->
				elif int(flagToCustomBinary(w[1])[4]) == 0 and strand == "+" and strandSA == "-": w.append("Inversion2")
				elif int(flagToCustomBinary(w[1])[4]) == 1 and strand == "-" and strandSA == "+": w.append("Inversion2")
				
				# reads <- <-
				elif int(flagToCustomBinary(w[1])[4]) == 0 and strand == "-" and strandSA == "+": w.append("Inversion1")
				elif int(flagToCustomBinary(w[1])[4]) == 1 and strand == "+" and strandSA == "-": w.append("Inversion1")
				
				# other potential SV not considered:
				else: w.append("NA")
		
		
		if len(set(w[-5:-1])) > 1 and w[-1] != "NA": # not NA only and DELETION/INVERSION specification
			JV_list.append("%s\n" %"\t".join([str(x) for x in w]))


	insertsplit.close() # we have a table with ID (1 column), insertsize or split positions (4 columns), corresponding VDJ genes (4 columns)
	
	return(JV_list)

def findCombinationsJandV(annot_table_JV, GENE):
	ANNOT_TABLE_JV = open(annot_table_JV, "r") # we use previous output file as input file

	l = list()
	for i in ANNOT_TABLE_JV:
		w=i.rstrip("\n").split("\t")
		
		r = []
		s = []
		
		for j in w[-5:-1]: # we take the four columns corresponding to V and J types for each insertSize and split positions
			if j != "NA": # if there exists information
				if j[3] not in r:
					r.append(j[3]) # we save letters corresponding to V and J ex: IGHV1-3 -> V, IGHJ2P -> J
					s.append([j, w[-5:-1].index(j)]) # we create sublists with V and J variants and the column number they belong
				else: # if list already contains the letter we are analysing (ex: s = [[V, 1],[J, 2]] and we are analysing V),
					  # we eliminate all information, as V can only match J and viceversa
					r = []
					s = []
			
			if w[-5:-1].index(j) == 1 or w[-5:-1].index(j) == 3: # second split or second insertSize
				if len(s) == 2: # if we find any type VJ, JV
					
					if GENE != "CSR":
						if [s[0][0]+" - "+s[1][0], w[-1]] not in l: # if not in list of pairs, add..
							l.append([s[0][0]+" - "+s[1][0], w[-1]])
					else:
						if "M" in r and [s[0][0]+" - "+s[1][0], w[-1]] not in l: # if it is class switch it must contain M
							l.append([s[0][0]+" - "+s[1][0], w[-1]])
				s = []
				r = []
	
	ANNOT_TABLE_JV.close()
	
	return(l)

def assignPositionsToJandV(l, annot_table_JV):
	
	VJ_positions = {} # we store pairs J-V positions and if they come from split/insertsize or both in some cases
	data = {} # we store count of pairs and individuals J/V by positions (from split) and by gene names (by insertSize) 
	pos = {}
	
	for k12 in l: # iterates over every sublist of pairs in list
		
		ANNOT_TABLE_JV = open(annot_table_JV, "r")
		for j in ANNOT_TABLE_JV:
			w=j.rstrip("\n").split("\t")
			
			for idx in [12, 14]:
				a = idx # first pos split/insert
				b = idx+1 # second pos split/insert
				
				if w[a] == "NA" or w[b] == "NA": continue
				
				srt = w[a+4]+" - "+w[b+4]
				srtPos = w[a]+" - "+w[b]
				readtype = w[20]
				
				if srt == k12[0] and readtype == k12[1]: # k12[0] = each pair, k12[1] = Deletion, Inversion1, Inversion2
					if srt not in VJ_positions:
						VJ_positions[k12[0]] = [[srtPos, "split" if idx == 12 else "insertSize", readtype]] 
					else:
						VJ_positions[k12[0]].append([srtPos, "split" if idx == 12 else "insertSize", readtype])
					
					if idx == 12:
						if srtPos+" - "+k12[1] not in data:
							data[srtPos+" - "+readtype] = 1
						else:
							data[srtPos+" - "+readtype] += 1
							
					else:
						if srt+" - "+readtype not in data:
							data[srt+" - "+readtype] = 1
						else:
							data[srt+" - "+readtype] += 1
		
		ANNOT_TABLE_JV.close()
		
		
		for key in VJ_positions: # dictionary of IGH from V and J position of start and end (specific for each rearrangement)
			spl = [] # save split position
			ins = [] # save insertSize position
			
			for m in VJ_positions[key]:
				if m[1] == "split":
					spl.append([m[0], m[2]]) # if info comes from split we save it on one list
				else:
					ins.append([m[0], m[2]]) # if info comes from insertSize we save it on another list
			
			# info from paired-split
			if len(spl) != 0:
				UNIQUEspl = []
				for s in spl:
					if s not in UNIQUEspl:
						UNIQUEspl.append(s) 
				pos[key] = UNIQUEspl
			
			# info from single-split (make all possible combinations)
			else: 
				ANNOT_TABLE_JV = open(annot_table_JV, "r")
				Jpos = []
				Vpos = []
				
				svClassInsert = [] # to get sv class from inserSize pairs
				for j in ANNOT_TABLE_JV:
					w=j.rstrip("\n").split("\t")
					if w[11].startswith("split") and key.split(" - ")[0] == w[16]:
						Jpos.append([w[12], w[20]]) # save all possible J positions comming individual splits
					elif w[11].startswith("split") and key.split(" - ")[1] == w[16]:
						Vpos.append([w[12], w[20]]) # save all possible V positions comming from individual splits
					
					if w[18] == key.split(" - ")[0] and w[19] == key.split(" - ")[1]: # key by insertSize reads to get SV class
						svClassInsert.append(w[20])
						
				ANNOT_TABLE_JV.close()
				
				svClassInsert = Counter(svClassInsert).most_common(1)[0][0] # Simplify to most common sv class

				UNIQUEjpos = []
				for x in Jpos:
					if x[1] == "NotComplete" or x[1] == svClassInsert:
						if x[0] not in UNIQUEjpos:
							UNIQUEjpos.append(x[0])

				UNIQUEvpos = []
				for y in Vpos:
					if y[1] == "NotComplete" or y[1] == svClassInsert:
						if y[0] not in UNIQUEvpos:
							UNIQUEvpos.append(y[0])

				JV = [[x+" - "+y, svClassInsert] for x in UNIQUEjpos for y in UNIQUEvpos] # we create all possible combinations if they have equal read orientation

				pos[key] = JV
				
				# info still no info, get info from paired-insertSize, unpaired insertSize and unpaired split
				if pos[key] == []:
					ANNOT_TABLE_JV = open(annot_table_JV, "r")
					Jpos = []
					Vpos = []
				
					svClassInsert = [] # to get sv class from inserSize pairs
					for j in ANNOT_TABLE_JV:
						w=j.rstrip("\n").split("\t")
						if key.split(" - ")[0] == w[16]:
							Jpos.append([w[12], w[20]]) 
						elif key.split(" - ")[1] == w[16]:
							Vpos.append([w[12], w[20]]) 
						if key.split(" - ")[0] == w[18]:
							Jpos.append([w[14], w[20]]) 
						elif key.split(" - ")[1] == w[18]:
							Vpos.append([w[14], w[20]]) 
						if key.split(" - ")[1] == w[19]:
							Vpos.append([w[15], w[20]]) 
					
						if w[18] == key.split(" - ")[0] and w[19] == key.split(" - ")[1]: # key by insertSize reads to get SV class
							svClassInsert.append(w[20])
						
					ANNOT_TABLE_JV.close()
					
					svClassInsert = Counter(svClassInsert).most_common(1)[0][0] # Simplify to most common sv class

					UNIQUEjpos = []
					for x in Jpos:
						if x[1] == "NotComplete" or x[1] == svClassInsert:
							if x[0] not in UNIQUEjpos:
								UNIQUEjpos.append(x[0])

					UNIQUEvpos = []
					for y in Vpos:
						if y[1] == "NotComplete" or y[1] == svClassInsert:
							if y[0] not in UNIQUEvpos:
								UNIQUEvpos.append(y[0])
					
					JV = [[x+" - "+y, svClassInsert] for x in UNIQUEjpos for y in UNIQUEvpos] # we create all possible combinations if they have equal read orientation
					
					pos[key] = JV
	
	return(VJ_positions, data, pos)

def addPositionsAndOccurrences(pos, bedFile, data):
	information = [] # list of sublists with pairs and information about them
	
	for key in pos:
		
		for i in range(len(pos[key])):
			
			keyJ = key.split(" - ")[0]
			keyV = key.split(" - ")[1]
			readtype = pos[key][i][1] # read type: INVERSION1,2 or DELETION
			keyPos = pos[key][i][0] # J-V positions split
			keyPosJ = int(keyPos.split(" - ")[0]) # last position for corresponding J
			keyPosV = int(keyPos.split(" - ")[1]) # first position for corresponding V
			
			row = [key, readtype] # we start adding V-J combination
			
			a = int(data.get(keyPos+" - "+readtype, 0)) # we find occurrences for corresponding V-J from split
			row.append(a)
			
			b = int(data.get(key+" - "+readtype, 0)) # we find occurrences for corresponding V-J from insertSize
			row.append(b)
			
			# find position in bed file (J)   
			c = "NA" 
			VDJ = open(bedFile, "r")
			for k in VDJ:
				v = k.rstrip("\n").split("\t")
				if keyJ == v[3]:
					if pos[key][i][1] == "Deletion":
						c = v[1]
						break
					elif pos[key][i][1] == "Inversion1":
						c = v[2]
						break
					elif pos[key][i][1] == "Inversion2":
						c = v[1]
						break
			row.extend(sorted([int(c), keyPosJ]))
			VDJ.close()	
			if row[-1] - row[-2] < 5: continue	
			
			# add 0 for split reads in J used in section 8
			row.append(0)
			
			
			# find position in bed file (V) 
			h = "NA" 
			VDJ = open(bedFile, "r")
			for k in VDJ:
				v = k.rstrip("\n").split("\t")
				if keyV == v[3]:
					if pos[key][i][1] == "Deletion":
						h = v[2] 
						break
					elif pos[key][i][1] == "Inversion1":
						h = v[2] 
						break
					elif pos[key][i][1] == "Inversion2":
						h = v[1]
						break

			VDJ.close()		
			row.extend(sorted([int(h), keyPosV]))
			if row[-1] - row[-2] < 10: continue
			
			# add 0 for split reads in V used in section 8
			row.append(0)
			
			information.append(row)
			
	return(information)

def getJandVsequences(information, GENE, refGenome, baseq, chromGene, bamN, miniBamT, miniBamN, depth, altDepth, tumorPurity, vafCutoff, vafCutoffNormal, pathToSamtools):
	
	if GENE == "IGL": # if IGL, switch V <-> J info
		for i in information:
			i[0] = i[0].split(" - ")[1]+" - "+i[0].split(" - ")[0]
			i4 = i[4]
			i5 = i[5]
			i[4] = i[7]
			i[5] = i[8]
			i[7] = i4
			i[8] = i5
	
	for i in information:
		temporary = []
		z = -6 # to iterate over positions for V,J
		while z < 0:
			
			if "Kde" in i[0] or "RSS" in i[0]: # no sequence to retrieve
				temporary.extend(["NA"]*2) 
				
			elif i[z] != "NA" and i[z+1] != "NA":
				
				if refGenome is None:
					fr = " -r "
				else:
					fr = " -f "+refGenome+" -r "
				
				subprocess.call(pathToSamtools+"samtools mpileup -B -A -Q "+baseq+fr+chromGene+":"+str(i[z])+"-"+str(i[z+1])+" "+miniBamT+ " > "+miniBamT.replace(".bam", "_output_mpileup.tsv"), shell=True) # allow -A (anomalous read pairs) in tumor sample only
				
				if os.stat(miniBamT.replace(".bam", "_output_mpileup.tsv")).st_size != 0:
					
					# Normal seq:
					if bamN is not None:
						subprocess.call(pathToSamtools+"samtools mpileup -B -Q "+baseq+fr+chromGene+":"+str(i[z])+"-"+str(i[z+1])+" "+miniBamN+ " > "+miniBamN.replace(".bam", "_output_mpileup.tsv"), shell=True)
						
						normal = open(miniBamN.replace(".bam", "_output_mpileup.tsv"), "r")
						wild = {} # normal patient sequence
						
						sq = int(i[z]) # starts at 1st position interval
						
						passar = 0

						for h in normal:
							w = h.rstrip("\n").split("\t")
							if passar == 0:
								g = 0 # saves possible snps in patient
								dna = {} # save possible snps 
								w[4] = w[4].replace(",", w[2]).replace(".", w[2]) # we change reference nucleotide
								w[4] = w[4].upper() # convert all nucleotides to uppercase 
								
								while g < len(w[4]): # look for ACGT in each position
									if w[4][g].isdigit():
										if w[4][g+1].isdigit(): s = 2 # insertion/deletion of > 9 bases
										else: s = 1 # insertion/deletion of < 10 bases
											
										prev = w[4][g-1] # previous shows + for insertions or - for deletions
										now = int(w[4][g:g+s]) # current number of nucleotides being added or removed
										indels = (w[4][g+s:g+s+now]) # nucleotides being added or removed
										
										if prev == "+": # insertion
											ins = w[4][g-2]+"["+indels+"]"
											if ins not in dna: # appends inserted region to dictionary
												dna[ins] = 1  
												dna[w[4][g-2]] -= 1
											else: # adds an occurrence in dictionary
												dna[ins] += 1
												dna[w[4][g-2]] -= 1
											g += now + 1  # we jump as many positions as number shows (number shows nucleotides inserted)
											
										elif prev == "-": # deletion
											dele = w[4][g-2]+"("+indels+")"
											if dele not in dna: # appends deleted region to dictionary
												dna[dele] = 1
												dna[w[4][g-2]] -= 1
											else: # adds an occurrence in dictionary
												dna[dele] += 1
												dna[w[4][g-2]] -= 1
											g += now + 1 # we jump as many positions as number shows (number shows nucleotides deleted)
											
										else: # workaround to exclude bases like ^6A (H/S/N in cigar)
											g += 2
											
									elif w[4][g] in ("A", "C", "G", "T"):
										if w[4][g] not in dna: # appends mutation to dictionary
											dna[w[4][g]] = 1
										else: # adds an occurrence in dictionary
											dna[w[4][g]] += 1
										g += 1
									
									else: # N, etc.
										g += 1
									
								
								dna = sorted(dna.items(), key=lambda dna: dna[1], reverse = True) # from high to low, the possible mutations
								
								tp = []
								if len(dna) > 0:
									for c in dna:
										if int(w[3]) > depth and c[1] > altDepth and (c[1]/int(w[3])) > vafCutoffNormal: # consider base if position depth > depth [default = 1], mut count > altDepth [default = 1] and vaf mutation > vafCutoffNormal [default = 0.20]
											tp.append(c[0])
								
								if len(tp) == 0:
									tp.append(w[2]) 

								
								if sq == int(w[1]): # positions in interval with info
									wild[sq] = tp # we append mutation to sequence instead of reference nucleotide
									
								else: # non existing positions
									while sq < int(w[1]):
										wild[sq] = ["N"]
										sq += 1
									wild[sq] = tp
									
								if len([True for x in wild[sq] if "(" in x]) > 0:
									wild[sq] = [x for x in wild[sq] if "(" in x]
									passar = len(wild[sq][0]) - 3  # ex: A(CA) -> 3 == A()
								
							else:
								passar -= 1
								
							sq += 1				
						
						# adjust length normal seq if nucleotides are missing
						while sq <= int(i[z+1]):
							wild[sq] = ["N"]
							sq += 1
							
						normal.close()
					
					else:
						wild = {}
						nuc = int(i[z+1])-int(i[z]) + 1
						for c in range(nuc):
							wild[int(i[z])+c] = ["N"]
					
					
					# Tumor seq:				
					current = open(miniBamT.replace(".bam", "_output_mpileup.tsv"), "r")
					tumSeq = []
					normSeq = []
					
					passar = 0 # used to jump sequences if there is a deletion in tumor sequence
					sq = int(i[z])
					
					for j in current:
						
						v=j.rstrip("\n").split("\t")
						
						v[4] = v[4].replace(",", v[2]).replace(".", v[2]) # we change reference nucleotide
						v[4] = v[4].upper() # convert all nucleotides to uppercase
						
						# check if missing positions
						while sq < int(v[1]):
							if passar == 0:
								# if indel in normal, we consider the indel independently of the tumor seq
								if len([True for x in wild[sq] if "(" in x or "[" in x]) > 0:
									if len([True for x in wild[sq] if "(" in x]) > 0:
										snps = [x for x in wild[sq] if "(" in x]
										passar = len(snps[0]) - 3  # ex: A(CA) -> 3 == A()
									else:
										snps = [x for x in wild[sq] if "]" in x]
									tumSeq.append(snps[0])
									normSeq.append(snps[0])
								else:
									tumSeq.append("N")
									normSeq.append(wild[sq][0])
								sq += 1
							else:
								passar -= 1
								sq += 1
								
						if passar == 0:
							
							newmut = {} # diccionary with nucleotide:n.ocurrences
							k = 0 # shows the number of sequences which have to be jumped
							
							while k < len(v[4]): # look for ACGT in each position
								if v[4][k].isdigit():
									if v[4][k+1].isdigit(): s = 2 # insertion/deletion of > 9 bases
									else: s = 1 # insertion/deletion of < 10 bases
									
									prev = v[4][k-1] # previous shows + for insertions or - for deletions
									now = int(v[4][k:k+s]) # current number of nucleotides being added or removed
									indels = (v[4][k+s:k+s+now]) # nucleotides being added or removed
									
									if prev == "+": # if it is insertion
										ins = v[4][k-2]+"["+indels+"]"
										if ins not in newmut: # appends inserted region to dictionary
											newmut[ins] = 1  
											newmut[v[4][k-2]] -= 1
										else: # adds an occurrence in dictionary
											newmut[ins] += 1
											newmut[v[4][k-2]] -= 1
										k += now + 1  # we jump as many positions as number shows (number shows nucleotides inserted)
										
									elif prev == "-": # if it is deletion
										dele = v[4][k-2]+"("+indels+")"
										if dele not in newmut: # appends deleted region to dictionary
											newmut[dele] = 1
											newmut[v[4][k-2]] -= 1
										else: # adds an occurrence in dictionary
											newmut[dele] += 1
											newmut[v[4][k-2]] -= 1
										k += now + 1 # we jump as many positions as number shows (number shows nucleotides deleted)
										
									else: # workaround to exclude bases like ^6A (H/S/N in cigar)
										k += 2
										
								elif v[4][k] in ("A", "C", "G", "T"):
									if v[4][k] not in newmut: # appends mutation to dictionary
										newmut[v[4][k]] = 1
									else: # adds an occurrence in dictionary
										newmut[v[4][k]] += 1
									k += 1
								
								else:
									k += 1
							
							
							newmut = sorted(newmut.items(), key=lambda newmut: newmut[1], reverse = True) # from high to low, the possible mutations
							
							snps = []
							other = []
							
							# check if nucleotide in normal seq, if not add the one from reference
							if wild[sq] == ["N"]:							
								wild[sq] = [v[2]]
							
							# if nucleotides in tumor newmut:
							if len(newmut) > 0: 
								for c in newmut:
									if int(v[3]) > depth and c[1] > altDepth and (c[1]/int(v[3])/tumorPurity) > vafCutoff: # min coverage > depth [default = 1], mut count > altDepth [default = 1] min VAF corrected by tumorPurity (if available) > vafCutoff [default = 0.10]
										if c[0] in wild[sq]:
											snps.append(c[0])
										else:
											other.append(c[0])
								
								# if indel in normal, we consider the indel independently of the tumor seq
								if len([True for x in wild[sq] if "(" in x or "[" in x]) > 0:
									if len([True for x in wild[sq] if "(" in x]) > 0:
										snps = [x for x in wild[sq] if "(" in x]
										passar = len(snps[0]) - 3  # ex: A(CA) -> 3 == A()
									else:
										snps = [x for x in wild[sq] if "]" in x]
									tumSeq.append(snps[0])
									normSeq.append(snps[0])
								
								# no indel in normal, and mutation in tumor
								elif len(other) > 0:
									tumSeq.append(other[0])
									if "(" in other[0] or "[" in other[0]:
										normSeq.append(other[0])
										if "(" in other[0]:
											passar = len(other[0]) - 3  # ex: A(CA) -> 3 == A()
									else:
										normSeq.append(wild[sq][0])
									
								# no indel in normal neither mutation in tumor, add fist SNP in both:
								elif len(snps) > 0: 
									tumSeq.append(snps[0])
									normSeq.append(snps[0])
								
								# else... add R:
								else:
									tumSeq.append("N")
									normSeq.append(wild[sq][0])
							
							# in case no newmut... 
							else:
								if len([True for x in wild[sq] if "(" in x or "[" in x]) > 0:
									if len([True for x in wild[sq] if "(" in x]) > 0:
										snps = [x for x in wild[sq] if "(" in x]
										passar = len(snps[0]) - 3  # ex: A(CA) -> 3 == A()
									else:
										snps = [x for x in wild[sq] if "]" in x]
									tumSeq.append(snps[0])
									normSeq.append(snps[0])
								else:
									tumSeq.append("N")
									normSeq.append(wild[sq][0])
						
						# passar != 0
						else:
							passar -= 1
						
						sq = int(sq) + 1
					
					current.close()
					
					# Adjust length tumor and normal if nucleotides missing:
					if sq-1 < int(i[z+1]):
						tumSeq.extend("N" * (int(i[z+1])-sq-1))
						
					if len(normSeq) < len(tumSeq):
						normSeq.extend("N" * (len(tumSeq)-len(normSeq)))
					
					if z == -3: # V
						temporary.append("".join(tumSeq)) # V seq tumor
						temporary.append("".join(normSeq)) # V seq normal
					
					else: # J -> add sequence of J and NA for D
						temporary.append(''.join(tumSeq)) # J seq
						temporary.append("") # empty for D seq
						
						
				else: # if no mpileup file
					temporary.extend(["NA"]*2) 
				
			else: # if no start-end
				temporary.extend(["NA"]*2) 
			
			z = z+3	# move from J to V start position index
			
			
		# Add temporary to i
		i.extend(temporary)
		
		if i[1] == "Inversion1":
			i[10] = ''.join(complement[base] for base in reversed(i[10])) 
		elif i[1] == "Inversion2":
			i[12] = ''.join(complement[base] for base in reversed(i[12]))
			i[13] = ''.join(complement[base] for base in reversed(i[13]))

	return(information)
	
def createConcensusD(DseqTemp, GENE, i, Dseqs):
	
	geneNames = i[0]
	
	DseqConsensus = list()
	
	for c in range(0, len(DseqTemp[0])):
		DseqConsensus.append(Counter([item[c] for item in DseqTemp]).most_common(1)[0][0])
	DseqConsensus = "".join(DseqConsensus)
	
	# check if insertion occurs at breaks (then the insertion is added at J/V in the mpileup and also present in the "D" sequence...remove it from "D"):
	if GENE != "IGL":
		j = i[10]
		v = i[12]
	else:
		j = i[12] # it is V
		v = i[10] # it is J
	
	if j[-1] == "]":
		if DseqConsensus.startswith(j[max([a.start()+1 for a in re.finditer("\[", j)]):-1]):
			DseqConsensus = DseqConsensus[len(j)-2-max([a.start()+1 for a in re.finditer("\[", j)])+1:]
			
	if v[0] == "[":
		if DseqConsensus.endswith(v[1:min([a.start()+1 for a in re.finditer("\]", v)])-1]):
			DseqConsensus = DseqConsensus[:len(DseqConsensus)-min([a.start()+1 for a in re.finditer("\]", v)])+2]
	
	# if IGH to check D gene:              
	if GENE == "IGH":
		sqs = open(Dseqs, "r")
		t = []
		for sqsLine in sqs:
			w = sqsLine.rstrip("\n").split("\t")
			score = smithwaterman(DseqConsensus, w[1])
			t.append([w[0], score])
		
		dGeneName = sorted(t, key=operator.itemgetter(1), reverse = True)[0][0]
		
		geneNames = " - ".join([i[0].split(" - ")[0], dGeneName, i[0].split(" - ")[1]]) # update J-V to J-D-V

	# add N-D-N / N
	return(geneNames, DseqConsensus)			


def getDsequence(information, annot_table_JV, GENE, Dseqs):
	
	toAddInInformation = [] # list to append to Information if same D with same length
	
	for i in information:
		
		# Get soft clipped start/end J-V :  
		if GENE != "IGL":
			breakJ = int(i[5])
			breakV = int(i[7])
		else:
			breakV = int(i[4]) # it is J 
			breakJ = int(i[8]) # it is V
		
		DseqTemp = []
		
		if "IGKKde" in i[0] or "IGKRSS" in i[0]:
			totseqW = "NA" # no totseq
			i.append(totseqW)
			
		else:
			reads = open(annot_table_JV, "r")
			for j in reads:
				w = j.rstrip("\n").split("\t")
				if w[11].startswith("split"):
					
					# if information last value J and first value V coincide with w split values
					if breakJ == int(w[12].replace("NA", "0")) and breakV == int(w[13].replace("NA", "0")):
						split = re.findall(r'[A-Za-z]|[0-9]+', w[5])
						cigar1 = [split[x:x+2] for x in range(0, len(split),2)]
						split = re.findall(r'[A-Za-z]|[0-9]+', w[10].split(",")[3])
						cigar2 = [split[x:x+2] for x in range(0, len(split),2)]
						# MS cigar
						if min([count for count, item in enumerate(cigar1) if "M" in item]) < min([count for count, item in enumerate(cigar1) if "S" in item]):
							mStart = sum([ int(x[0]) if x[1] in ["M", "I"] else 0 for x in cigar1 ]) # we add the numbers previous to M and I
							mEnd = sum([ int(x[0]) if x[1] == "S" else 0 for x in cigar2 ]) # we add numbers previous to S
						# SM cigar
						else:
							mStart = sum([ int(x[0]) if x[1] in ["M", "I"] else 0 for x in cigar2 ]) # we add the numbers previous to M and I
							mEnd = sum([ int(x[0]) if x[1] == "S" else 0 for x in cigar1 ]) # we add numbers previous to S
						
						DseqTemp.append(w[9][mStart:mEnd]) # we analyse from M,I+seq until seq-everything but S
						
					
					# if information last position J:
					elif breakJ == int(w[12].replace("NA", "0")) and w[13] == "NA":
							
						split = re.findall(r'[A-Za-z]|[0-9]+', w[5])
						cigar1 = [split[x:x+2] for x in range(0, len(split),2)]
						# MS cigar
						if min([count for count, item in enumerate(cigar1) if "M" in item]) < min([count for count, item in enumerate(cigar1) if "S" in item]):
							mStart = sum([ int(x[0]) if x[1] == "S" else 0 for x in cigar1 ]) # we add numbers previous to S
							J = w[9][-mStart:]
						# SM cigar
						else:
							mEnd = sum([ int(x[0]) if x[1] == "S" else 0 for x in cigar1 ]) # we add numbers previous to S
							J = w[9][:mEnd]
						
						# Vseq: remove deleted nucleotides, check insertion at first bases, keep insertions not at first base:
						if GENE != "IGL": 
							vSeq = re.sub("\(.*?\)", "",  i[12])
							if vSeq[0] == "[":
								vSeq = vSeq[min([a.start()+1 for a in re.finditer("\]", vSeq)]):]
						
						else: # it is J in IGL
							vSeq = re.sub("\(.*?\)", "",  i[10])
							if vSeq[-1] == "]":
								vSeq = vSeq[:max([a.start() for a in re.finditer("\[", vSeq)]):]
						
						vSeq = vSeq.replace("[", "").replace("]", "")
						
						j = 0
						while j <= len(J)-5:
							if vSeq.startswith(J[j:]):
								DseqTemp.append(J[:j])
								if GENE != "IGL": i[6] += 1 # count split J
								else: i[9] += 1 # count split V
								break
							j += 1
					
					# if information first position V:
					elif breakV == int(w[12].replace("NA", "0")) and w[13] == "NA":
						
						split = re.findall(r'[A-Za-z]|[0-9]+', w[5])
						cigar1 = [split[x:x+2] for x in range(0, len(split),2)]
						# MS cigar
						if min([count for count, item in enumerate(cigar1) if "M" in item]) < min([count for count, item in enumerate(cigar1) if "S" in item]):
							mStart = sum([ int(x[0]) if x[1] == "S" else 0 for x in cigar1 ]) # we add numbers previous to S
							V = w[9][-mStart:]
						# SM cigar
						else:
							mEnd = sum([ int(x[0]) if x[1] == "S" else 0 for x in cigar1 ]) # we add numbers previous to S
							V = w[9][:mEnd]
						
						# jSeq: remove deleted nucleotides, check insertion at last bases, keep insertions not at last base:
						if GENE != "IGL": 
							jSeq = re.sub("\(.*?\)", "",  i[10])
							if jSeq[-1] == "]":
								jSeq = jSeq[:max([a.start() for a in re.finditer("\[", jSeq)]):]
						else:  # it is V in IGL
							jSeq = re.sub("\(.*?\)", "",  i[12])
							if jSeq[0] == "[":
								jSeq = jSeq[min([a.start()+1 for a in re.finditer("\]", jSeq)]):]
								
						jSeq = jSeq.replace("[", "").replace("]", "")

						v = len(V)
						while v >= 5:
							if jSeq.endswith(V[:v]):
								DseqTemp.append(V[v:])
								if GENE != "IGL": i[9] += 1 # count split V
								else: i[6] += 1 # count split J
								break
							v -= 1
			
			reads.close()
			
			# Report Ds:	
			AorBdone = "no"		
			if len(DseqTemp) > 0: 
				
				## A) all possible "D"s have different lengths... keep them all...
				if len(set([len(s) for s in DseqTemp])) == len(DseqTemp): 
					
					countToAdd = 1
					for DseqTempSimple in DseqTemp:
						geneNames, DseqConsensus = createConcensusD([DseqTempSimple], GENE, i, Dseqs)
						if countToAdd < len(DseqTemp):
							iToAddInToAddInInformationlist = i.copy()
							iToAddInToAddInInformationlist[0] = geneNames
							iToAddInToAddInInformationlist[11] = DseqConsensus
							if GENE != "IGL":
								totseqW = iToAddInToAddInInformationlist[10]+iToAddInToAddInInformationlist[11]+iToAddInToAddInInformationlist[12]
							else:
								totseqW = iToAddInToAddInInformationlist[12]+iToAddInToAddInInformationlist[11]+iToAddInToAddInInformationlist[10]
							totseqW = re.sub("\(.*?\)", "", totseqW.replace("[", "").replace("]", ""))
							iToAddInToAddInInformationlist.append(totseqW)
							
							toAddInInformation.append(iToAddInToAddInInformationlist)
							
						else:
							i[0] = geneNames
							i[11] = DseqConsensus
							if GENE != "IGL":
								totseqW = i[10]+i[11]+i[12]
							else:
								totseqW = i[12]+i[11]+i[10]
							totseqW = re.sub("\(.*?\)", "", totseqW.replace("[", "").replace("]", ""))
							i.append(totseqW)
						
						countToAdd += 1
					
					AorBdone = "yes"
				
				
				## B) if not, and first and second D lengths have the same number of supporting reads -> keep both!
				elif len(set([len(s) for s in DseqTemp])) >= 2: 
					
					if Counter([len(s) for s in DseqTemp]).most_common(2)[0][1] == Counter([len(s) for s in DseqTemp]).most_common(2)[1][1]:
						
						# get first
						DseqTempSimple = [ss for ss in DseqTemp if len(ss) == Counter([len(s) for s in DseqTemp]).most_common(2)[0][0]] # get Dseqs with the same length	
						geneNames, DseqConsensus = createConcensusD(DseqTempSimple, GENE, i, Dseqs)
						iToAddInToAddInInformationlist = i.copy()
						iToAddInToAddInInformationlist[0] = geneNames
						iToAddInToAddInInformationlist[11] = DseqConsensus
						if GENE != "IGL":
							totseqW = iToAddInToAddInInformationlist[10]+iToAddInToAddInInformationlist[11]+iToAddInToAddInInformationlist[12]
						else:
							totseqW = iToAddInToAddInInformationlist[12]+iToAddInToAddInInformationlist[11]+iToAddInToAddInInformationlist[10]
						totseqW = re.sub("\(.*?\)", "", totseqW.replace("[", "").replace("]", ""))
						iToAddInToAddInInformationlist.append(totseqW)
						toAddInInformation.append(iToAddInToAddInInformationlist)
						
						# get second
						DseqTempSimple = [ss for ss in DseqTemp if len(ss) == Counter([len(s) for s in DseqTemp]).most_common(2)[1][0]] # get Dseqs with the same length	
						geneNames, DseqConsensus = createConcensusD(DseqTempSimple, GENE, i, Dseqs)
						i[0] = geneNames
						i[11] = DseqConsensus
						if GENE != "IGL":
							totseqW = i[10]+i[11]+i[12]
						else:
							totseqW = i[12]+i[11]+i[10]
						totseqW = re.sub("\(.*?\)", "", totseqW.replace("[", "").replace("]", ""))
						i.append(totseqW)
						
						AorBdone = "yes"
						
				
				## C) if not A or B, get Dseqs with the same length
				if AorBdone == "no":
					DseqTemp = [ss for ss in DseqTemp if len(ss) == Counter([len(s) for s in DseqTemp]).most_common(1)[0][0]] # get Dseqs with the same length		
					geneNames, DseqConsensus = createConcensusD(DseqTemp, GENE, i, Dseqs)
					i[0] = geneNames
					i[11] = DseqConsensus
					
					if GENE != "IGL":
						totseqW = i[10]+i[11]+i[12]
					else:
						totseqW = i[12]+i[11]+i[10]
					totseqW = re.sub("\(.*?\)", "", totseqW.replace("[", "").replace("]", ""))
					i.append(totseqW)
			
			
			## D) No D... just concatenate sequence
			else:
				if GENE != "IGL":
					totseqW = i[10]+i[11]+i[12]
				else:
					totseqW = i[12]+i[11]+i[10]
				totseqW = re.sub("\(.*?\)", "", totseqW.replace("[", "").replace("]", ""))
				i.append(totseqW)
	
	
	information.extend(toAddInInformation) # extend information with duplicated entries with different D (from previous A and B)
	return(information)

def calculateHomology(hom, homN):
	ct = 0 # sum total nucleotides
	ce = 0 # sum equal nucleotides
	j = 0
	g = 0
	
	while j < len(hom):
		if hom[j] != "N" and homN[j] != "N":	
			ct += 1
			if homN[j] == hom[j]:
				ce += 1
		j += 1
	if ct > len(hom)/2:
		pctHomology = str(round((ce/ct)*100, 3)) # homology
		numHomology = str(ce)+"/"+str(ct) # number nucleotides homology
	else:
		pctHomology = "NA"
		numHomology = "NA"
	
	return(pctHomology, numHomology)

def productivityAndCDR3(vdj, nCDR3):
	
	# set output
	productiu = "NA"
	aaCDR3 = "NA"
	
	vdjTrip = re.findall('.{3}', vdj)

	# stop codons in seq:
	if "TAA" in vdjTrip or "TAG" in vdjTrip or "TGA" in vdjTrip:
		productiu1 = "Unproductive (stop codons)"
	else:
		productiu1 = "Phe118 not identified (check at IMGT/IgBlast)"

	if 'TTT' in nCDR3 or 'TTC' in nCDR3 or 'TGG' in nCDR3:
		
		
		for wf in reversed(list(re.finditer('TTT|TTC|TGG', nCDR3, overlapped=True))): 
			
			j118 = "NA"
			
			productiu = productiu1	# re-set productiu
			
			po = wf.start()
			
			tripMotif = re.findall('.{3}', nCDR3[po:po+12])
			
			if len(tripMotif) == 4:           
				if "N" in tripMotif[1]: continue
		
				if "N" in tripMotif[3]: 
					if tripletsToAA[tripMotif[1]] == "G":
						j118 = po+3
		
				elif tripletsToAA[tripMotif[1]] == "G" or tripletsToAA[tripMotif[3]] == "G":
					j118 = po+3
			
			elif len(tripMotif) > 1 and "N" not in tripMotif[1]:
				if tripletsToAA[tripMotif[1]] == "G":
					j118 = po+3
			
			if j118 != "NA": 
				nCDR3_a = nCDR3[:j118]
		
				# out-of-frame
				if not (len(nCDR3_a)/3).is_integer(): 				
					if productiu == "Unproductive (stop codons)": productiu = "Unproductive (stop codons, out-of-frame junction)"
					else: productiu = "Unproductive (out-of-frame junction)"
			
					if ((len(nCDR3_a)+1)/3).is_integer(): add = "."
					else: add = ".."
					nCDR3_a = nCDR3_a[:-9]+add+nCDR3_a[-9:]
					tripCDR3 = re.findall('.{3}', nCDR3_a)  
					aaCDR3 = "".join([tripletsToAA[aa] if "." not in aa and "N" not in aa else "?" if "N" in aa else "#" for aa in tripCDR3])
			
				# in frame
				else: 
					if productiu == "Unproductive (stop codons)":
						productiu = "Unproductive (stop codons, in-frame junction)"
					else: 
						productiu = "Productive (no stop codon and in-frame junction)"
					
					tripCDR3 = re.findall('.{3}', nCDR3_a)
					aaCDR3 = "".join([tripletsToAA[aa] if "N" not in aa else "?" for aa in tripCDR3])
			
					if productiu == "Productive (no stop codon and in-frame junction)": break

			elif j118 == "NA":# and productiu == "Phe118 not identified (check at IMGT/IgBlast)":
				nCDR3_a = nCDR3
				tripCDR3 = re.findall('.{3}', nCDR3_a)
				aaCDR3 = "".join([tripletsToAA[aa] if "N" not in aa else "?" for aa in tripCDR3])
				if productiu == "Unproductive (stop codons)": productiu = "Unproductive (stop codons, Phe118 not identified)"
	
	else:
		productiu = productiu1
		if productiu == "Unproductive (stop codons)": productiu = "Unproductive (stop codons, Phe118 not identified)"
		nCDR3_a = nCDR3
		tripCDR3 = re.findall('.{3}', nCDR3_a)
		aaCDR3 = "".join([tripletsToAA[aa] if "N" not in aa else "?" for aa in tripCDR3])
		
	return(productiu, aaCDR3)

def checkHomologyAndFunctionality(information, GENE):
	
	for p in information:
		
		lstProductiu = ["NA"]*5
		productiu, aaCDR3, pctHomology, numHomology, hom = lstProductiu
		
		if "Kde" not in p[0] and "RSS" not in p[0]:
			
			productiu = "No junction found"
			
			# remove insertions from V to check productivity (but keep deletions):
			tumSeq = re.sub("\[.*?\]", "", p[-3]).replace("(", "").replace(")", "")
			normSeq = re.sub("\[.*?\]", "", p[-2]).replace("(", "").replace(")", "")


			if GENE != "IGL":
				t = ''.join(complement[base] for base in reversed(tumSeq))+''.join(complement[base] for base in  reversed(p[-4]))  # reverse complement of V + D
				n = ''.join(complement[base] for base in reversed(normSeq))+''.join(complement[base] for base in  reversed(p[-4])) # reverse complement of V normal + D tumor
			else:
				t = tumSeq+p[-4] # V tumor + D tumor
				n = normSeq+p[-4] # V normal + D tumor
			
			# Check: Cys23 (Trp41) Cys104 to define FR1-FR3 for homology		
			for cys in reversed(list(re.finditer('TGT|TGC', t, overlapped=True))): 
				
				countAAfound = 1 # count cys23, trp41, cys104, phe118 found
				
				if productiu.startswith("Productive") or productiu.startswith("Phe118 not identified"): break # if already found
			
				posCys104 = "NA"
				
				po = int(cys.start()) # Cys23 
				substractLeft = 21 # 21 and not 22 because usually aa10 is missing
				if po-substractLeft*3 < 0: continue # make sure potential Cys23 is not just at the the begining of the sequence
				
				nextpo = po + 14*3 if GENE == "IGH" else po + 9*3 # Trp41 (9 aa x 3bp) 
				
				if nextpo > len(t): continue
				
				# Trp41
				if "TGG" in re.findall('.{3}', t[nextpo:nextpo+30]): 
					
					countAAfound += 1 
					
					nextpo += max([i for i in range(len(re.findall('.{3}', t[nextpo:nextpo+30]))) if re.findall('.{3}', t[nextpo:nextpo+30])[i] == 'TGG']) * 3 
					nextnextpo = nextpo + 58*3 if GENE == "IGH" else nextpo + 48*3 # for cys 104
					
					if nextnextpo > len(t): continue
					
					# Cys104
					if 'TGT' in re.findall('.{3}', t[nextnextpo:nextnextpo+36]) or 'TGC' in re.findall('.{3}', t[nextnextpo:nextnextpo+36]):
						countAAfound += 1 
						posCys104 = [ nextnextpo + cysUnref * 3 + 3 for cysUnref in [i for i in range(len(re.findall('.{3}', t[nextnextpo:nextnextpo+36]))) if re.findall('.{3}', t[nextnextpo:nextnextpo+36])[i] == 'TGT' or re.findall('.{3}', t[nextnextpo:nextnextpo+36])[i] == 'TGC'] ] #+3 for index 0             ################33333333 36
				
				# No Trp41, check Cys104 directly	
				else: 
					nextnextpo = nextpo + 58*3 if GENE == "IGH" else nextpo + 48*3 # for cys 104
					if 'TGT' in re.findall('.{3}', t[nextnextpo:nextnextpo+36]) or 'TGC' in re.findall('.{3}', t[nextnextpo:nextnextpo+36]):
						countAAfound += 1 
						
						posCys104 = [ nextnextpo + cysUnref * 3 + 3 for cysUnref in [i for i in range(len(re.findall('.{3}', t[nextnextpo:nextnextpo+36]))) if re.findall('.{3}', t[nextnextpo:nextnextpo+36])[i] == 'TGT' or re.findall('.{3}', t[nextnextpo:nextnextpo+36])[i] == 'TGC'] ] #+3 for index 0
						
				# Check homolgy and functionality if Cys104 found
				if posCys104 != "NA":
					
					posCys104_list = posCys104    
					
					for posCys104 in posCys104_list:		
						
						vSeq = t[po-substractLeft*3:] # to be used for cdr3: store FR1 - endOfV
						newPosCys104 = posCys104-3-(po-substractLeft*3) # to be used for cdr3: get position Cys104 from FR1, not from beggining of V gene
						hom = t[po-substractLeft*3:posCys104]
						homN = n[po-substractLeft*3:posCys104]							
						
						# calculateHomology:
						pctHomology, numHomology = calculateHomology(hom, homN)
						
						# if complete (D found for IGH or not IGH and FR1-FR3 found previously), check if productive and get CDR3:
						if ((GENE == "IGH" and p[-4] != "") or GENE != "IGH") and hom != "NA":
							if GENE != "IGL":
								j = ''.join(complement[base] for base in reversed(re.sub("\(.*?\)", "", p[-5]).replace("[", "").replace("]", ""))) # remove deletions only from J to check productivity
							else:
								j = re.sub("\(.*?\)", "", p[-5].replace("[", "").replace("]", "")) # remove deletions only from J to check productivity
							
							# VDJ sequence and CDR3
							vdj = vSeq+j
							nCDR3 = vdj[newPosCys104:].rstrip("N") 
							
							# productivityAndCDR3
							productiu, aaCDR3 = productivityAndCDR3(vdj, nCDR3)
							
							if lstProductiu == ["NA"]*5 or productiu.startswith("Productive"):
								lstProductiu = [ productiu, aaCDR3, pctHomology, numHomology, hom ]

							if productiu.startswith("Productive"): break
			
			productiu, aaCDR3, pctHomology, numHomology, hom = lstProductiu
			
			
			# if productive rearrangement not found starting with Cys23, start at Trp41:
			lstProductiu_2 = ["NA"]*5	
			productiu_2, aaCDR3_2, pctHomology_2, numHomology_2, hom_2 = lstProductiu_2
			
			if not productiu.startswith("Productive"):
				# Trp41
				for trp in reversed(list(re.finditer('TGG', t, overlapped=True))): 
					
					if productiu_2.startswith("Productive") or productiu_2.startswith("Phe118 not identified"): break # if already found
					
					posCys104 = "NA"
					
					nextpo = int(trp.start()) # Trp41 (we add 1 as index start at 0)
					if GENE == "IGH":
						substractLeft = 35 # not 40 because aa10 is usually missing and 4 aa usually missing at CDR1
					else:
						substractLeft = 33 # not 40 because aa10 is usually missing and 6 aa usually missing at CDR1
					
					if nextpo-substractLeft*3 < 0: continue # make sure potential Trp41 is not at the the begining of the sequence
							
					
					nextnextpo = nextpo + 58*3 if GENE == "IGH" else nextpo + 48*3 # for cys 104
					
					
					# Cys104
					if 'TGT' in re.findall('.{3}', t[nextnextpo:nextnextpo+36]) or 'TGC' in re.findall('.{3}', t[nextnextpo:nextnextpo+36]): 
						
						posCys104_list = [ nextnextpo + cysUnref * 3 + 3 for cysUnref in [i for i in range(len(re.findall('.{3}', t[nextnextpo:nextnextpo+36]))) if re.findall('.{3}', t[nextnextpo:nextnextpo+36])[i] == 'TGT' or re.findall('.{3}', t[nextnextpo:nextnextpo+36])[i] == 'TGC'] ] #+3 for index 0
						
						# check homolgy and functionality	
						for posCys104 in posCys104_list:
							
							# check homolgy and functionality								
							vSeq = t[nextpo-substractLeft*3:] # to be used for cdr3: store FR1 - endOfV
							newPosCys104 = posCys104-3-(nextpo-substractLeft*3) # to be used for cdr3: get position Cys104 from FR1, not from beggining of V gene
							hom_2 = t[nextpo-substractLeft*3:posCys104]
							homN = n[nextpo-substractLeft*3:posCys104]							
							
							
							# calculateHomology
							pctHomology_2, numHomology_2 = calculateHomology(hom_2, homN)
						
							
							# if complete (D found for IGH or not IGH and FR1-FR3 found previously), check if productive and get CDR3 sequence:
							if ((GENE == "IGH" and p[-4] != "") or GENE != "IGH") and hom_2 != "NA":
								if GENE != "IGL":
									j = ''.join(complement[base] for base in reversed(re.sub("\(.*?\)", "", p[-5]).replace("[", "").replace("]", ""))) # remove deletions only from J to check productivity
								else:
									j = re.sub("\(.*?\)", "", p[-5]).replace("[", "").replace("]", "") # remove deletions only from J to check productivity
					
								# VDJ sequence and CDR3
								vdj = vSeq+j
								nCDR3 = vdj[newPosCys104:].rstrip("N") 
								
								# productivityAndCDR3
								productiu_2, aaCDR3_2 = productivityAndCDR3(vdj, nCDR3)
								
								if lstProductiu_2 == ["NA"]*5 or productiu_2.startswith("Productive"):
									lstProductiu_2 = [ productiu_2, aaCDR3_2, pctHomology_2, numHomology_2, hom_2 ]
								
								if productiu_2.startswith("Productive") or productiu_2.startswith("Phe118 not identified") : break	
			
			productiu_2, aaCDR3_2, pctHomology_2, numHomology_2, hom_2 = lstProductiu_2
			
			# merge starting at Cys23 and Trp41:
			if productiu_2.startswith("Productive") or ( productiu.startswith("Unproductive") and productiu_2.startswith("Phe118 not identified") ) or  ( productiu == "Unproductive (stop codons, out-of-frame junction)" and productiu_2 == "Unproductive (stop codons, in-frame junction)" ):
				productiu = productiu_2
				aaCDR3 = aaCDR3_2
				pctHomology = pctHomology_2
				numHomology = numHomology_2
				hom = hom_2
			
			elif productiu.startswith("Unproductive") and productiu_2.startswith("Unproductive"):
				if len(aaCDR3_2) < len(aaCDR3):
					productiu = productiu_2
					aaCDR3 = aaCDR3_2
					pctHomology = pctHomology_2
					numHomology = numHomology_2
					hom = hom_2
			
			
			# if no homolgy calculated before, determine homology entire V gene:			
			if pctHomology == "NA":
				t = tumSeq # V tumor
				n = normSeq # V normal				
				pctHomology, numHomology = calculateHomology(t, n)
			
			if "[" in p[-3] or "(" in p[-3]: # or "[" in p[-5] or "(" in p[-5]
				productiu = productiu+" [indel(s) in seq]"
				
		p.append(pctHomology)
		p.append(numHomology)
		p.append(productiu)
		p.append(aaCDR3)
		
	return(information)

def predefinedFilter(information, GENE, tumorPurity, seq):
	
	trip = {} # dict to save passing rearrangements
	kdeCount = 2
	
	for line in information:
		
		pr = 0
		
		spl_ins = round( ( int(line[2])*2 + int(line[3]) + int(line[6])*2 + int(line[9])*2 ) / tumorPurity , 1 )
		
		# hard filters
		if spl_ins < 3: continue  # 1 split and 1 insertSize required
		elif spl_ins == 3 and "Productive" not in line[17]: continue  # more than 1 split and 1 insertSize required for unproductive

		
		if "Kde" not in line[0] and "RSS" not in line[0]:
			if seq == "wgs" and sum(1 for i in line[12] if i == "N")/len(line[12]) > 0.5: continue # remove rearrangement if >50% of the V sequence are "N"s for WGS-derived samples
			elif sum(1 for i in line[10] if i == "N")/len(line[10]) > 0.5: continue # remove rearrangement if >50% of the J sequence are "N"s
			
			if len(line[12]) < 20: continue  # remove rearrangement if length V < 20bp
		
		elif "Kde" in line[0] and "RSS" in line[0]: # remove Kde-RSS if only 1 split read
			if int(line[2]) < 2: continue
		
		# soft filters
		if len(trip) == 0:
			trip[line[0]] = [line[1], spl_ins]+line[2:]
			
		else:
			# if exactly the same VDJ is already annotated...
			if line[0] in trip: 
				dict_spl_ins = trip[line[0]][1]
				
				if "Kde" not in line[0] and "RSS" not in line[0]:
					
					# Productive:
					if "Productive" not in trip[line[0]][17] and "Productive" in line[17]:
						trip[line[0]] = [line[1], spl_ins]+line[2:] # add new if productive and the one in trip is unproductive
					elif "Productive" in trip[line[0]][17] and "Productive" not in line[17]:
						pass # if the annotated is productive while the new one unproductive
					
					# Phe118 not identified
					elif not trip[line[0]][17].startswith("Phe118 not identified") and line[17].startswith("Phe118 not identified"):
						trip[line[0]] = [line[1], spl_ins]+line[2:] # new phe118 not identified, annotated unproductive
					elif trip[line[0]][17].startswith("Phe118 not identified") and not line[17].startswith("Phe118 not identified"):
						pass # if annotated is phe118 not identified, new unproductibe
					
					# if both have the same functionality... keep the one with higher score
					elif spl_ins > dict_spl_ins:
						trip[line[0]] = [line[1], spl_ins]+line[2:]
					elif dict_spl_ins > spl_ins:
						pass
					
					# if both have the same count...
					elif "Productive" not in trip[line[0]][17] and "Productive" not in line[17]: # if both are unproductive just keep the one already annotated in trip
						pass
					else: # if both are productive, keep based on CDR3 length
						if len(line[18]) > len(trip[line[0]][18]):
							trip[line[0]] = [line[1], spl_ins]+line[2:]
				
				elif "Kde" in line[0] and "RSS" in line[0]:
					trip[line[0]+" ("+str(kdeCount)+")"] = [line[1], spl_ins]+line[2:]
					kdeCount += 1
				
				else:
					if spl_ins > dict_spl_ins:
						trip[line[0]] = [line[1], spl_ins]+line[2:]
					else: # if same score take the one with "Deletion"
						if line[1] == "Deletion" and trip[line[0]][1] != "Deletion":
							trip[line[0]] = [line[1], spl_ins]+line[2:]
						
			# if not exact VDJ...
			else:
				
				for keys in [k for k in trip]: # make list of keys to avoid dictionary changed size during iteration
					ts = keys.split(" - ") # annotated values
					nw = line[0].split(" - ") # new value
					common = set(ts).intersection(nw) # intersection between values in dict and value analysed
					dict_spl_ins = trip[keys][1]
					# at least >1 gene in common, check the best one
					if len(common) > 1: 
						if len(ts) > len(nw): # if the one annotated has len=3 (VDJ) and he new one 2 (VJ), keep the one annotated
							pr = 1 
						elif len(ts) < len(nw): # if the other way around... keep the new one
							pr = 1
							del trip[keys]
							trip[line[0]] = [line[1], spl_ins]+line[2:]
						
						# if len == 2 in both...
						elif "Productive" not in trip[keys][17] and "Productive" in line[17]: # if new is productive
							pr = 1
							del trip[keys]
							trip[line[0]] = [line[1], spl_ins]+line[2:]
						elif "Productive" in trip[keys][17] and "Productive" not in line[17]: # if annjotated is productive
							pr = 1 
						elif not trip[keys][17].startswith("Phe118 not identified") and line[17].startswith("Phe118 not identified"):  # new phe118 not identified, annotated unproductive
							pr = 1
							del trip[keys]
							trip[line[0]] = [line[1], spl_ins]+line[2:]
						elif trip[keys][17].startswith("Phe118 not identified") and not line[17].startswith("Phe118 not identified"):  # if annotated is phe118 not identified, new unproductibe
							pr = 1
							
						# if both have the same functionality... keep the one with higher score
						elif spl_ins > dict_spl_ins: 
							pr = 1
							del trip[keys]
							trip[line[0]] = [line[1], spl_ins]+line[2:]
						elif spl_ins < dict_spl_ins: 
							pr = 1 
						elif "Productive" not in trip[keys][17] and "Productive" not in line[17]: # if both are unproductive just keep the one already annotated in trip
							pr = 1 
						elif len(line[18]) >= len(trip[keys][18]): # if both are productive, keep based on CDR3 length
							pr = 1
							del trip[keys]
							trip[line[0]] = [line[1], spl_ins]+line[2:]
							
					elif len(common) == 1 and GENE == "IGK": # add to simplify IGKVX and IGKVDX (ie. IGKV1 and IGKVD1) equally productive rearrangements
						if keys.replace("D", "") == line[0] or keys == line[0].replace("D", ""): # same IGKV but with "D" (i.e. same gene but in distal cluster --> high homology, low mapping quality!)
							if spl_ins > dict_spl_ins:
								pr = 1
								del trip[keys]
								trip[line[0]] = [line[1], spl_ins]+line[2:]
							elif dict_spl_ins > spl_ins:
								pr = 1
							else: # if same score take the one without "D"
								if keys.replace("D", "") == line[0]:
									pr = 1
									del trip[keys]
									trip[line[0]] = [line[1], spl_ins]+line[2:]
								else:
									pr = 1
							break		
					
				if pr == 0: # no estava al diccionari
					trip[line[0]] = [line[1], spl_ins]+line[2:]
	
	return(trip)

def addMapQualAndScore(information, trip, GENE, annot_table_JV):
	for i in information:
		if GENE != "IGL":
			if i[1] == "Deletion":
				breakJ = int(i[5])
				breakV = int(i[7])
			elif i[1] == "Inversion2":
				breakJ = int(i[5])
				breakV = int(i[8])
			elif i[1] == "Inversion1":
				breakJ = int(i[4])
				breakV = int(i[7])
			J = i[0].split(" - ")[0]
			V = i[0].split(" - ")[-1]
		
		else:
			if i[1] == "Deletion":
				breakV = int(i[4]) # it is J 
				breakJ = int(i[8]) # it is V
			elif i[1] == "Inversion2":
				breakV = int(i[5])
				breakJ = int(i[8])
			elif i[1] == "Inversion1":
				breakV = int(i[4])
				breakJ = int(i[7])
			
			V = i[0].split(" - ")[0] # it is J 
			J = i[0].split(" - ")[-1] # it is V
		
		
		spl_ins = int(i[2])*2 + int(i[3]) + int(i[6])*2 + int(i[9])*2
		quals = []
		reads = open(annot_table_JV, "r")
		for read in reads:
			readList = read.rstrip("\n").split("\t")
			if ( readList[11].startswith("split") and int(readList[12] if readList[12] != "NA" else 0) == breakJ and int(readList[13] if readList[13] != "NA" else 0) == breakV ) or ( J == readList[18] and V == readList[19] ):
				quals.append(int(readList[4]))
		reads.close()
		
		if quals == []: MQ = "NA"
		else: MQ = str(round(mean(quals),1))+" ("+str(min(quals))+"-"+str(max(quals))+")"

		i.append(spl_ins)
		i.append(MQ)
		
		for t in trip:
			if i[4] == trip[t][4] and i[5] == trip[t][5] and i[7] == trip[t][7] and i[8] == trip[t][8]:
				trip[t].append(MQ) 
				break
	
	return(information, trip)

def classSwitchAnalysis(data, bedFile, baseq, chromGene, bamT, bamN, pathToSamtools, tumorPurity):
	class_switch = []
	class_switch_filt = []
	reductionMeans  = []
	#~ pvals = []
	
	for key in data:
		kGenes = key.split(" - ")[0]+" - "+key.split(" - ")[1]
		kReadtype = key.split(" - ")[2]
		
		score = round(data[key] / tumorPurity, 1)
		
		# hard filter:
		if score < 4 or kReadtype != "Deletion": continue # keep only class switch rearrangmenet if supported by >= 5 insertSize reads and  by "Deletion"
		
		# study coverage and soft filter:
		isotypye = kGenes.split(" - ")[0]
		
		VDJ = open(bedFile, "r")
		for k in VDJ:
			v = k.rstrip("\n").split("\t")
			if isotypye == v[3]:
				startA = int(v[1])-1500
				endA = int(v[1])
				startB = int(v[2])
				endB = int(v[2])+1500
				break
		VDJ.close()		
		
		covs = {}
		for i in ["A", "B"]:
			if i == "A":
				st = startA
				en = endA							
			else:
				st = startB
				en = endB
			
			subprocess.call(pathToSamtools+"samtools mpileup -B -Q "+baseq+" -r "+chromGene+":"+str(st)+"-"+str(en)+" "+bamT+ " > "+bamT.replace(".bam", "_output_mpileup.tsv"), shell=True)					
			
			pos = st
			lst = []
			seq = open(bamT.replace(".bam", "_output_mpileup.tsv"), "r")
			for sLine in seq:
				sList = sLine.rstrip("\n").split("\t")
				while pos < int(sList[1]):
					lst.append(0)
					pos += 1
				lst.append(int(sList[3]))
				pos += 1
			seq.close()
			
			while pos <= en:
				lst.append(0)
				pos += 1	
				
			covs[i] = lst
		
		meanA = round(mean(covs["A"]), 3)
		meanB = round(mean(covs["B"]), 3)
		
		meanNormA = 1
		meanNormB = 1

		# if normal bam file available, substract depth in normal to correct for different distribution of coverage and correct means to positive
		if bamN != None:
			
			forMeanNorm = []		
			for i in ["A", "B"]:
				if i == "A":
					st = startA
					en = endA							
				else:
					st = startB
					en = endB
				
				subprocess.call(pathToSamtools+"samtools mpileup -B -Q "+baseq+" -r "+chromGene+":"+str(st)+"-"+str(en)+" "+bamN+ " > "+bamN.replace(".bam", "_output_mpileup.tsv"), shell=True)					
				
				pos = st
				idx = 0
				seq = open(bamN.replace(".bam", "_output_mpileup.tsv"), "r")
				for sLine in seq:
					sList = sLine.rstrip("\n").split("\t")
					while pos < int(sList[1]):
						covs[i][idx] = covs[i][idx] - 0
						forMeanNorm.append(0)
						idx += 1
						pos += 1
					covs[i][idx] = covs[i][idx] - int(sList[3])
					forMeanNorm.append(int(sList[3]))
					idx += 1
					pos += 1
				seq.close()
				
				if i == "A":
					meanNormA = mean(forMeanNorm)
				else:
					meanNormB = mean(forMeanNorm)
		
		
		# adjusted meanA to ratio means in normal
		meanA = round(meanA/(meanNormA/meanNormB), 3)
		
		# wilcoxon
		statistic, pvalue = stats.wilcoxon(covs["A"], covs["B"])
		
		# reduction adjusted means adjusted by tumor purity
		reductionMean = round(100-(meanB/meanA*100), 3) / tumorPurity
				
		# hard filter:
		if reductionMean > 0:
			class_switch.append([ kGenes.split(" - ")[0], kReadtype, score, meanA, meanB, pvalue, reductionMean ])
		
		# pre-defined soft filer:
		if meanA > 8 and reductionMean >= 30 and pvalue < 0.0000000001: # 1e-10
			if (score >= 4 and reductionMean >= 60) or (score >= 7 and reductionMean >= 30):
				class_switch_filt.append([ kGenes.split(" - ")[0], kReadtype, score, meanA, meanB, pvalue, reductionMean ])
				reductionMeans.append(reductionMean)
				#~ pvals.append(pvalue)
	
	class_switch = sorted(class_switch, key=operator.itemgetter(1), reverse=True)
	
	return(class_switch, class_switch_filt, reductionMeans)

def getIgTranslocations(pathToSamtools, threadsForSamtools, bamT, bamN, chrom, coordsToSubset, tumorPurity, mntonco, mntoncoPass, mnnonco, mapqOnco):
	
	chrom14 = coordsToSubset.split(" ")[0].split(":")[1].split("-") # IGH region 
	chrom22 = coordsToSubset.split(" ")[1].split(":")[1].split("-") # IGL region
	chrom2 = coordsToSubset.split(" ")[2].split(":")[1].split("-") # IGK region
	
	chroms = [chrom+str(i) for i in range(1,22)]+[chrom+"X", chrom+"Y", "="] # chroms considered ("=" to consider deletions/inversions/gains within the same chromosome)
	
	samT = bamT.replace(".bam", ".sam")
	comms = pathToSamtools+"samtools view -@ "+threadsForSamtools+" -q "+mapqOnco+" "+bamT+" > "+samT 
	subprocess.call(comms, shell=True)
	
	if bamN is not None:
		samN = bamN.replace(".bam", ".sam")
		comms = pathToSamtools+"samtools view -@ "+threadsForSamtools+" -q "+mapqOnco+" "+bamN+" > "+samN 
		subprocess.call(comms, shell=True)
	
	# 1. annotate potential 1-read translocations
	dicForTranslocations = {} 
	dicForTranslocations[chrom+"14"] = {}
	dicForTranslocations[chrom+"2"] = {}
	dicForTranslocations[chrom+"22"] = {}

	samfile = open(samT, "r")
	for i in samfile:
		
		w = i.rstrip("\n").split("\t")
		sa=[]
		for x in (w[11:]): # get SA:... after qualities
			if x.startswith("SA:Z"):
				sa.append(x)
		if len(sa) != 0: w = w[:10]+[sa[0]]
		else: w = w[:10]+["NA"]
		
		if w[5] != "*" and w[6] in chroms:
			if w[6] == "=":
				if abs(int(w[3]) - int(w[7])) > 10000: # for inversion, deletions, gains
					if w[2] == chrom+"14" and int(w[7]) >= int(chrom14[0]) and int(w[7]) <= int(chrom14[1]): continue
					elif w[2] == chrom+"22" and int(w[7]) >= int(chrom22[0]) and int(w[7]) <= int(chrom22[1]): continue
					elif w[2] == chrom+"2" and int(w[7]) >= int(chrom2[0]) and int(w[7]) <= int(chrom2[1]): continue
				else: continue
				
			flgBin = flagToCustomBinary(w[1])
			split1 = re.findall(r'[A-Za-z]|[0-9]+', w[5])
			two1 = [split1[x:x+2] for x in range(0, len(split1),2)]
			
			inChrom = w[2]
			posInChrom = w[3]
			strandInChrom = "-" if "1" == flgBin[4] else "+"
			if strandInChrom == "+": posInChrom = str(int(posInChrom) + sum([int(i[0]) for i in two1 if "M" in i or "D" in i]) - 1)
			
			# if split, get second break from split:
			strandOutChrom = "-" if "1" == flgBin[5] else "+" # strand from insert size to get orientation of the translocation
			if w[10].startswith("SA:Z") and w[10].split(":")[2].split(",")[0] in chroms:
				outChrom = w[10].split(":")[2].split(",")[0]
				posOutChrom = w[10].split(":")[2].split(",")[1]
				strandOutChromSA = w[10].split(":")[2].split(",")[2]
				if strandOutChromSA == "-":
					split1 = re.findall(r'[A-Za-z]|[0-9]+', w[10].split(":")[2].split(",")[3])
					two1 = [split1[x:x+2] for x in range(0, len(split1),2)]
					posOutChrom = str(int(posOutChrom) + sum([int(i[0]) for i in two1 if "M" in i or "D" in i]) - 1)
			else: # else, get from insertsize
				outChrom = w[6].replace("=", inChrom)
				posOutChrom = w[7]
			
			if outChrom in dicForTranslocations[inChrom]:
				dicForTranslocations[inChrom][outChrom].append([posInChrom, strandInChrom, posOutChrom, strandOutChrom])
			else:
				dicForTranslocations[inChrom][outChrom] = [[posInChrom, strandInChrom, posOutChrom, strandOutChrom]]
				
	samfile.close()
	subprocess.call("rm "+samT, shell=True)	
	
	# 2. Merge individual one-read translocations into potential translocations (kep only if number of reads (ie score) > mntonco)
	translocations = {}
	translocations[chrom+"14"] = {}
	translocations[chrom+"2"] = {}
	translocations[chrom+"22"] = {}
	
	position1 = list()
	strand1 = ""
	position2 = list()
	strand2 = ""
	for key1 in dicForTranslocations:
		for key2 in dicForTranslocations[key1]:
			for item in dicForTranslocations[key1][key2]:
				alreadyConsidered = "no"
				
				# check if new one-read translocation could be added to an already merged potential translocation;
				if key2 in translocations[key1]:
					for item2 in translocations[key1][key2]:
						if ( abs(int(item[0]) - int(item2[1])) < 1000 or abs(int(item[0]) - int(item2[2])) < 1000 ) and item[1] == item2[3] and ( abs(int(item[2]) - int(item2[5])) < 1000 or abs(int(item[2]) - int(item2[6])) < 1000 )  and item[3] == item2[7]:
							item2[1] = str(min([int(item2[1]), int(item[0])]))
							item2[2] = str(max([int(item2[2]), int(item[0])]))
							item2[5] = str(min([int(item2[5]), int(item[2])]))
							item2[6] = str(min([int(item2[6]), int(item[2])]))
							item2[8] = item2[8]+1
							alreadyConsidered = "yes"
							break
				
				# if not added before, initialize new potential translocation:
				if alreadyConsidered == "no":
					if position1 == list():
						position1.append(int(item[0]))
						strand1 = item[1]
						position2.append(int(item[2]))
						strand2 = item[3]
						alreadyConsidered = "yes"
					
					elif  min(abs(p1 - int(item[0])) for p1 in position1) < 1000 and strand1 == item[1] and min(abs(p2 - int(item[2])) for p2 in position2) < 1000 and strand2 == item[3]:
						position1.append(int(item[0]))
						position2.append(int(item[2]))
				
					else:
						if len(position1) >= mntonco:
							if key2 in translocations[key1]: translocations[key1][key2].append([key1, str(min(position1)), str(max(position1)), strand1, key2, str(min(position2)), str(max(position2)), strand2, len(position1), 0 if bamN is not None else "NA"]) # 0 will be the count in normal
							else: translocations[key1][key2] = [ [key1, str(min(position1)), str(max(position1)), strand1, key2, str(min(position2)), str(max(position2)), strand2, len(position1), 0 if bamN is not None else "NA"] ]
					
						position1 = [int(item[0])]
						strand1 = item[1]
						position2 = [int(item[2])]
						strand2 = item[3]
						
			# if no more positions in second chrom, end iteration and reset:
			if len(position1) >= mntonco:
				if key2 in translocations[key1]: translocations[key1][key2].append([key1, str(min(position1)), str(max(position1)), strand1, key2, str(min(position2)), str(max(position2)), strand2, len(position1), 0 if bamN is not None else "NA"])
				else: translocations[key1][key2] = [ [key1, str(min(position1)), str(max(position1)), strand1, key2, str(min(position2)), str(max(position2)), strand2, len(position1), 0 if bamN is not None else "NA"] ]
				
				position1 = list()
				strand1 = ""
				position2 = list()
				strand2 = ""
	
	# 3. Annotate in normal
	if bamN is not None:
		samfile = open(samN, "r")
		for i in samfile:
			
			w = i.rstrip("\n").split("\t")
			sa=[]
			for x in (w[11:]): # get SA:... after qualities
				if x.startswith("SA:Z"):
					sa.append(x)
			if len(sa) != 0: w = w[:10]+[sa[0]]
			else: w = w[:10]+["NA"]
			
			if w[5] != "*" and w[6] in chroms: 
				if w[6] == "=":
					if abs(int(w[3]) - int(w[7])) > 8000: # 8000 instead of 10000 just to be more permessive in the normal...
						if w[2] == chrom+"14" and int(w[7]) >= int(chrom14[0]) and int(w[7]) <= int(chrom14[1]): continue
						elif w[2] == chrom+"22" and int(w[7]) >= int(chrom22[0]) and int(w[7]) <= int(chrom22[1]): continue
						elif w[2] == chrom+"2" and int(w[7]) >= int(chrom2[0]) and int(w[7]) <= int(chrom2[1]): continue
					else: continue
				
				flgBin = flagToCustomBinary(w[1])
				split1 = re.findall(r'[A-Za-z]|[0-9]+', w[5])
				two1 = [split1[x:x+2] for x in range(0, len(split1),2)]
				
				inChrom =  w[2]
				posInChrom = int(w[3])
				strandInChrom = "-" if "1" == flgBin[4] else "+"
				if strandInChrom == "+": posInChrom = posInChrom + sum([int(i[0]) for i in two1 if "M" in i or "D" in i]) - 1
				
				# if split, get second break from split:
				strandOutChrom = "-" if "1" == flgBin[5] else "+"
				if w[10].startswith("SA:Z") and w[10].split(":")[2].split(",")[0] in chroms:
					outChrom = w[10].split(":")[2].split(",")[0]
					posOutChrom = int(w[10].split(":")[2].split(",")[1])
					strandOutChromSA = w[10].split(":")[2].split(",")[2]
					if strandOutChromSA == "-":
						split1 = re.findall(r'[A-Za-z]|[0-9]+', w[10].split(":")[2].split(",")[3])
						two1 = [split1[x:x+2] for x in range(0, len(split1),2)]
						posOutChrom = posOutChrom + sum([int(i[0]) for i in two1 if "M" in i or "D" in i]) - 1
				else: # else, get from insertsize
					outChrom = w[6].replace("=", inChrom)
					posOutChrom = int(w[7])
				
				if outChrom not in translocations[inChrom]: continue
				for trans in translocations[inChrom][outChrom]:
					if trans[0] == inChrom and int(trans[1])-1000 <= posInChrom and int(trans[2])+1000 >= posInChrom and trans[3] == strandInChrom and trans[4] == outChrom and int(trans[5])-1000 <= posOutChrom and int(trans[6])+1000 >= posOutChrom and trans[7] == strandOutChrom:
						trans[9] = trans[9]+1
		
		samfile.close()
		subprocess.call("rm "+samN, shell=True)	
	
	# 4. Prepare output and return
	translocationsList = []
	for key1 in translocations:
		for key2 in translocations[key1]:
			for item in translocations[key1][key2]: 
				translocationsList.append(item)
	
	translocationsList = sorted(translocationsList, key=operator.itemgetter(8), reverse=True)
	translocationsALL = list()
	translocationsPASS = list()
	translocationsALL.append("\t".join(["Rearrangement", "Mechanism", "Score", "Reads in normal", "ChrA", "PositionA", "StrandA", "ChrB", "PositionB", "StrandB"]))
	
	for i in translocationsList:
		
		if i[0] == i[4]:
			if int((i[1] if i[3] == "-" else i[2])) < int((i[5] if i[7] == "-" else i[6])):
				idxA = 0
				idxB = 4
			else:
				idxA = 4
				idxB = 0
			
			chrA = i[idxA]
			strandA = i[idxA+3]
			positionA = i[idxA + (2 if strandA == "+" else 1)]
			chrB = i[idxB]
			strandB = i[idxB+3]
			positionB = i[idxB + (2 if strandB == "+" else 1)]
			
			if strandA == "+" and strandB == "-": 
				mechanism = "Deletion"
				traAnnot = "del("+chrA+":"+positionA+"-"+positionB+")"
			
			elif strandA == "-" and strandB == "+": 
				mechanism = "Gain"
				traAnnot = "gain("+chrA+":"+positionA+"-"+positionB+")"
			else: 
				mechanism = "Inversion"
				traAnnot = "inv("+chrA+":"+positionA+"-"+positionB+")"
		
		else:
			mechanism = "Translocation"
			
			traAnnot = ("t("+str(min([int(i[0].replace("chr", "").replace("X", "23").replace("Y", "24")), int(i[4].replace("chr", "").replace("X", "23").replace("Y", "24"))]))+";"+str(max([int(i[0].replace("chr", "").replace("X", "23").replace("Y", "24")), int(i[4].replace("chr", "").replace("X", "23").replace("Y", "24"))]))+")").replace("23", "X").replace("24", "Y")
			
			if i[0].replace("chr", "") == traAnnot.replace("t(", "").split(";")[0]: 
				idxA = 0
				idxB = 4
			else: 
				idxA = 4
				idxB = 0
			
			chrA = i[idxA]
			strandA = i[idxA+3]
			positionA = i[idxA + (2 if strandA == "+" else 1)]
			chrB = i[idxB]
			strandB = i[idxB+3]
			positionB = i[idxB + (2 if strandB == "+" else 1)]
			
		score = round( i[8] / tumorPurity, 1 ) 
		scoreNormal = i[9]	
		translocationsALL.append("\t".join([traAnnot, mechanism, str(score), str(scoreNormal), chrA, positionA, strandA, chrB, positionB, strandB]))
	
		# Pass
		if score >= mntoncoPass and ( scoreNormal == "NA" or scoreNormal <= mnnonco ):
			if mechanism == "Translocation": traAnnot = traAnnot+" ["+chrA+":"+positionA+":"+strandA+";"+chrB+":"+positionB+":"+strandB+"]"
			else: traAnnot = traAnnot+" ["+strandA+"/"+strandB+"]"
			translocationsPASS.append("\t".join(["Oncogenic IG rearrangement", traAnnot, mechanism, str(score)+" ("+str(scoreNormal)+")"]+["NA"]*6))
	
	return(translocationsALL, translocationsPASS)
