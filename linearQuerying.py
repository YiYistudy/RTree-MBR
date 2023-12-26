import os
from sys import argv, exit
from ast import literal_eval
from time import sleep, time
try:
	from tqdm import tqdm
	isTqdmAvailable = True
except:
	isTqdmAvailable = False
try:
	os.chdir(os.path.abspath(os.path.dirname(__file__))) # cd into the location path of this script
except: # it does not work in Jupyter-notebook
	pass
EXIT_SUCCESS = 0
EXIT_FAILURE = 1
defaultTime = 5
coordsFilepath = "coords.txt"
rTreeFilepath = "Rtree.txt"
queriesFilepath = "NNqueries.txt"
linearScanningCoordsResultsFilepath = "linearScanningCoordsResults.txt"
linearScanningMBRsResultsFilepath = "linearScanningMBRsResults.txt"


# class #
class RTreeNode:
	def __init__(self, entries = [], id = 0, MBR = None):
		self.entries = entries
		self.id = id
		self.MBR = MBR
	def __str__(self) -> str:
		if isinstance(self.entries[0], RTreeNode):
			return str([1, self.id, [[entry.id, entry.MBR] for entry in self.entries]])
		else:
			return str([0, self.id, self.entries])


# get input #
def getTxt(filepath, index = 0) -> str: # get .txt content
	coding = ("utf-8", "gbk", "utf-16") # codings
	if 0 <= index < len(coding): # in the range
		try:
			with open(filepath, "r", encoding = coding[index]) as f:
				content = f.read()
			return content[1:] if content.startswith("\ufeff") else content # if utf-8 with BOM, remove BOM
		except (UnicodeError, UnicodeDecodeError):
			return getTxt(filepath, index + 1) # recursion
		except:
			return None
	else:
		return None # out of range

def getCoordsWithID(coordsFp = coordsFilepath) -> list:
	content = getTxt(coordsFp)
	if content is None:
		return None
	content = content.replace("\r", "\n") # filtering "\r"
	while "\n\n" in content: # filtering empty lines
		content = content.replace("\n\n", "\n")
	coords = []
	for cnt, line in enumerate(content.split("\n")):
		if line.count(",") == 1:
			tmp = line.split(",")
			try:
				coords.append([float(tmp[0]), float(tmp[1]), cnt])
			except:
				print("Line {0} has been skipped since converting error occured. ".format(cnt))
		elif line: # it is not necessary to prompt the empty line
			print("Line {0} has been skipped since the count of comma(s) is not 1. ".format(cnt))
	return coords

def getRTree(rTreeFp = rTreeFilepath) -> list:
	content = getTxt(rTreeFp)
	if content is None:
		return None
	content = content.replace("\r", "\n") # filtering "\r"
	while "\n\n" in content: # filtering empty lines
		content = content.replace("\n\n", "\n")
	try:
		rTreeDict = {}
		for line in content.split("\n"):
			if line.startswith("[") and line.endswith("]"):
				lists = literal_eval(line)
				if lists[1] in rTreeDict:
					print("Repeated entry: id = {0}".format(lists[1]))
				else:
					rTreeDict[lists[1]] = RTreeNode(entries = lists[2], id = lists[1])
					if lists[0]: # if it is a non-leaf node
						for entry_idx, element in enumerate(lists[2]):
							if element[0] in rTreeDict:
								rTreeDict[lists[1]].entries[entry_idx] = rTreeDict[element[0]]
							else:
								print("Entry not found: id = {0}".format(element[0]))
		return rTreeDict[max(rTreeDict.keys())] # the largest id is the root (excluding the leaf node)
	except:
		return None

def checkRTreeMBR(rTree) -> bool:
	try:
		if isinstance(rTree, RTreeNode):
			if rTree.MBR[0] <= rTree.MBR[1] and rTree.MBR[2] <= rTree.MBR[3]:
				for entry in rTree.entries:
					if not checkRTreeMBR(entry):
						return False
				return True
			else:
				return False
		else: # list
			return rTree[1][0] <= rTree[1][1] and rTree[1][2] <= rTree[1][3]
	except:
		return False

def getQueries(queriesFp = queriesFilepath) -> list:
	content = getTxt(queriesFp)
	if content is None:
		return None
	content = content.replace("\r", "\n") # filtering "\r"
	while "\n\n" in content: # filtering empty lines
		content = content.replace("\n\n", "\n")
	queries = []
	for cnt, line in enumerate(content.split("\n")):
		if line.count(" ") in (1, 3):
			tmp = line.split(" ")
			try:
				queries.append([float(tmp[0]), float(tmp[2]), float(tmp[1]), float(tmp[3])] if len(tmp) == 4 else [float(tmp[0]), float(tmp[1])])
			except:
				print("Line {0} has been skipped since converting error occured. ".format(cnt))
		elif line: # it is not necessary to prompt the empty line
			print("Line {0} has been skipped since the count of space(s) is not 1 or 3. ".format(cnt))
	return queries

def computeNodeMBR(nodes) -> list: # find the bounds
	if nodes:
		x_low = min(nodes, key = lambda c:c[0])[0]
		x_high = max(nodes, key = lambda c:c[1])[1]
		y_low = min(nodes, key = lambda c:c[2])[2]
		y_high = max(nodes, key = lambda c:c[3])[3]
		return [x_low, x_high, y_low, y_high]
	else:
		return None

def computeRTreeMBR(rTree) -> None:
	if isinstance(rTree.entries[0], RTreeNode):
		for entry in rTree.entries:
			if entry.MBR is None:
				computeRTreeMBR(entry)
		rTree.MBR = computeNodeMBR([entry.MBR for entry in rTree.entries])
	else:
		rTree.MBR = computeNodeMBR([entry[1] for entry in rTree.entries])


# handle querying #
def linearScanningCoords(coords, q, k) -> list:
	linearScanningResults = []
	for coord in coords:
		linearScanningResults.append((coord, ((coord[0] - q[0]) ** 2 + (coord[1] - q[1]) ** 2) ** (1 / 2)))
	linearScanningResults.sort(key = lambda x:x[1])
	return [item[0][2] for item in linearScanningResults[:k]]

def doLinearScanningCoords(coords, queries, k) -> list:
	linearScanningResults = []
	for query in (tqdm(queries, ncols = 80) if isTqdmAvailable else queries):
		linearScanningResults.append([query, linearScanningCoords(coords, query, k)])
	return linearScanningResults

def isOverlap(rect1, rect2) -> bool: # [x_low, x_high, y_low, y_high]
	return rect1[0] <= rect2[1] and rect1[1] >= rect2[0] and rect1[2] <= rect2[3] and rect1[3] >= rect2[2]

def _linearScanningRanges(rTree, q, init_list) -> None:
	if isinstance(rTree, RTreeNode):
		for entry in rTree.entries:
			_linearScanningRanges(entry, q, init_list)
	elif isOverlap(rTree[1], q):
		init_list.append(rTree[0])

def linearScanningRanges(rTree, q) -> list:
	linearScanningResults = []
	_linearScanningRanges(rTree, q, linearScanningResults)
	return linearScanningResults

def distance(rectangle, q) -> float:
	x_distance = 0 if rectangle[0] <= q[0] <= rectangle[1] else min(abs(rectangle[0] - q[0]), abs(rectangle[1] - q[0]))
	y_distance = 0 if rectangle[2] <= q[1] <= rectangle[3] else min(abs(rectangle[2] - q[1]), abs(rectangle[3] - q[1]))
	return (x_distance ** 2 + y_distance ** 2) ** (1 / 2)

def _linearScanningMBRs(rTree, q, init_list) -> None:
	if isinstance(rTree, RTreeNode):
		for entry in rTree.entries:
			_linearScanningMBRs(entry, q, init_list)
	else:
		init_list.append((rTree, distance(rTree[1], q)))

def linearScanningMBRs(rTree, q, k) -> list:
	linearScanningResults = []
	_linearScanningMBRs(rTree, q, linearScanningResults)
	linearScanningResults.sort(key = lambda x:x[1])
	return [item[0][0] for item in linearScanningResults[:k]]

def doLinearScanningMBRs(rTree, queries, k) -> list:
	linearScanningResults = []
	for query in (tqdm(queries, ncols = 80) if isTqdmAvailable else queries):
		if len(query) == 4:
			linearScanningResults.append([query, linearScanningRanges(rTree, query)])
		else:
			linearScanningResults.append([query, linearScanningMBRs(rTree, query, k)])
	return linearScanningResults


# make output #
def output(linearScanningResults, outputFp = None, encoding = "utf-8") -> bool:
	if outputFp:
		try:
			with open(outputFp, "w", encoding = encoding) as f:
				for i, result in enumerate(linearScanningResults):
					f.write("{0} ({1}): {2}\n".format(i, len(result[1]), ",".join([str(item) for item in result[1]])))
			print("Dump to the result file successfully. ")
			return True
		except Exception as e:
			print("Error writing output file. ")
			print(e)
			return False
	for i, result in enumerate(linearScanningResults):
		print("{0} ({1}): {2}".format(i, len(result[1]), ",".join([str(item) for item in result[1]])))
	return True



# main function #
def preExit(countdownTime = defaultTime) -> None: # we use this function before exiting instead of getch since getch is not OS-independent
	try:
		cntTime = int(countdownTime)
		length = len(str(cntTime))
	except:
		return
	print()
	while cntTime > 0:
		print("\rProgram ended, exiting in {{0:>{0}}} second(s). ".format(length).format(cntTime), end = "")
		try:
			sleep(1)
		except:
			print("\rProgram ended, exiting in {{0:>{0}}} second(s). ".format(length).format(0))
			return
		cntTime -= 1
	print("\rProgram ended, exiting in {{0:>{0}}} second(s). ".format(length).format(cntTime))

def printHelp() -> None:
	print("Python script for KNN querying by linear scanning. ", end = "\n\n")
	print("Option: ")
	print("\t[/coords|--coords|coords]: Specify that the following option is the input coords file. ")
	print("\t[/rTree|--rTree|rTree]: Specify that the following option is the input rTree file. ")
	print("\t[/queries|--queries|queries]: Specify that the following option is the input querying file. ")
	print("\t[/k|-k|k]: Specify that the following option is the input k. ")
	print("\t[/o|-o|o|/output|--output|output]: Specify that the following option is the output result file. ", end = "\n\n")
	print("Format: ")
	print("\tpython linearQuerying.py [/rTree|--rTree|rTree] rTreeFilepath [/queries|--queries|queries] queriesFilepath [/k|-k|k] k [/o|-o|o|/output|--output|output] outputFilepath")
	print("\tpython linearQuerying.py [/coords|--coords|coords] coordsFilepath [/queries|--queries|queries] queriesFilepath [/k|-k|k] k [/o|-o|o|/output|--output|output] outputFilepath", end = "\n\n")
	print("Example: ")
	print("\tpython linearQuerying.py /rTree rTree.txt /queries NNqueries.txt /k 10 /output linearScanningMBRsResults.txt")
	print("\tpython linearQuerying.py /coords coords.txt /queries NNqueries.txt /k 10 /output linearScanningCoordsResults.txt", end = "\n\n")
	print("Note: You should specify only \"[/coords|--coords|coords]\" option or \"[/rTree|--rTree|rTree]\" option at a time. In case of conflicts, the last one shall prevail. If a query datum contains four numbers, the range querying would be performed. Please note that no pruning methods will be used in linear scanning though the R-tree file is read. It is read just for loading all the fundamental MBRs. ", end = "\n\n")

def handleCommandline() -> dict:
	for arg in argv[1:]:
		if arg.lower() in ("/h", "-h", "h", "/help", "--help", "help", "/?", "-?", "?"):
			printHelp()
			return True
	if len(argv) > 1 and len(argv) not in (3, 5, 7, 9):
		print("The count of the commandline options is incorrect. Please check your commandline. ")
		return False
	dicts = {"coords":coordsFilepath, "rTree":rTreeFilepath, "queries":queriesFilepath, "k":10, "output":None, "queryMBR":None}
	pointer = None
	for arg in argv[1:]:
		if arg.lower() in ("/coords", "--coords", "coords"):
			pointer = "coords"
			dicts["queryMBR"] = False
		elif arg.lower() in ("/rtree", "--rtree", "rtree"):
			pointer = "rTree"
			dicts["queryMBR"] = True
		elif arg.lower() in ("/queries", "--queries", "queries"):
			pointer = "queries"
		elif arg.lower() in ("/k", "-k", "k"):
			pointer = "k"
		elif arg.lower() in ("/o", "-o", "o", "/output", "--output", "output"):
			pointer = "output"
		elif pointer is None:
			print("Error handling commandline, please check your commandline. ")
			return False
		else:
			dicts[pointer] = arg
			pointer = None # reset
	try:
		dicts["k"] = int(dicts["k"])
	except:
		print("Error regarding k as an integer. Please check your commandline. ")
		return False
	return dicts

def main() -> int:
	# get input #
	commandlineArgument = handleCommandline()
	if type(commandlineArgument) == bool:
		return EXIT_SUCCESS if commandlineArgument else EXIT_FAILURE
	while commandlineArgument["queryMBR"] is None:
		tmp = input("Query top k nearest fundamental MBRs or coords? Enter Y for MBRs or N for coords. ")
		if tmp.upper() == "Y":
			commandlineArgument["queryMBR"] = True
		elif tmp.upper() == "N":
			commandlineArgument["queryMBR"] = False
	if commandlineArgument["output"] is None:
		commandlineArgument["output"] = linearScanningMBRsResultsFilepath if commandlineArgument["queryMBR"] else linearScanningCoordsResultsFilepath
	if commandlineArgument["queryMBR"]:
		rTree = getRTree(commandlineArgument["rTree"])
		if rTree is None:
			print("Error reading RTree, please check. ")
			preExit()
			return EXIT_FAILURE
		computeRTreeMBR(rTree)
		if not checkRTreeMBR(rTree):
			print("Check RTree MBR failed. Please check your input RTree file. ")
			preExit()
			return EXIT_FAILURE
	else:
		coords = getCoordsWithID(commandlineArgument["coords"])
		if coords is None:
			print("Error reading coords, please check. ")
			preExit()
			return EXIT_FAILURE
	queries = getQueries(commandlineArgument["queries"])
	if queries is None:
		print("Error reading queries, please check. ")
		preExit()
		return EXIT_FAILURE
	
	# handle queries #
	print("Start to perform linear scanning. It may take a while to finish the process. ")
	start_time = time()
	if commandlineArgument["queryMBR"]:
		linearScanningResults = doLinearScanningMBRs(rTree, queries, commandlineArgument["k"])
	else:
		linearScanningResults = doLinearScanningCoords(coords, queries, commandlineArgument["k"])
	end_time = time()
	if commandlineArgument["queryMBR"]:
		if len(queries):
			print("Total time: {0:.3f}s. Item count: {1}. Average Time: {2:.3f}ms/item. ".format(end_time - start_time, len(queries), (end_time - start_time) / len(queries) * 1000))
		else:
			print("Nothing queried since the querying list is empty. ")
	else:
		if len(queries):
			print("Total time: {0:.3f}s. Item count: {1}. Coord count: {2}. Average Time: {3:.3f}ms/item. ".format(end_time - start_time, len(queries), len(coords), (end_time - start_time) / len(queries) * 1000))
		else:
			print("Nothing queried since the querying list is empty. ")
	
	# make output #
	output(linearScanningResults, outputFp = commandlineArgument["output"])
	preExit()
	return EXIT_SUCCESS





if __name__ == "__main__":
	exit(main())