import os
from sys import argv, exit
from ast import literal_eval
from time import sleep, time
try:
	os.chdir(os.path.abspath(os.path.dirname(__file__))) # cd into the location path of this script
except: # it does not work in Jupyter-notebook
	pass
EXIT_SUCCESS = 0
EXIT_FAILURE = 1
defaultTime = 5
rTreeFilepath = "Rtree.txt"
rQueriesFilepath = "Rqueries.txt"
rangeResultsFilepath = "rangeResults.txt"


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

def getQueries(rQueriesFp = rQueriesFilepath) -> list:
	content = getTxt(rQueriesFp)
	if content is None:
		return None
	content = content.replace("\r", "\n") # filtering "\r"
	while "\n\n" in content: # filtering empty lines
		content = content.replace("\n\n", "\n")
	queries = []
	for cnt, line in enumerate(content.split("\n")):
		if line.count(" ") == 3:
			tmp = line.split(" ")
			try:
				queries.append([float(tmp[0]), float(tmp[2]), float(tmp[1]), float(tmp[3])]) # swap to [x_low, x_high, y_low, y_high]
			except:
				print("Line {0} has been skipped since converting error occured. ".format(cnt))
		elif line: # it is not necessary to prompt the empty line
			print("Line {0} has been skipped since the count of space(s) is not 3. ".format(cnt))
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
def isOverlap(rect1, rect2) -> bool: # [x_low, x_high, y_low, y_high]
	return rect1[0] <= rect2[1] and rect1[1] >= rect2[0] and rect1[2] <= rect2[3] and rect1[3] >= rect2[2]

def rQuerying(rTree, W, init_list = []) -> None:
	if isinstance(rTree, RTreeNode):
		if isOverlap(rTree.MBR, W):
			for entry in rTree.entries:
				rQuerying(entry, W, init_list)
	else:
		if isOverlap(rTree[1], W):
			init_list.append(rTree[0])

def doRangeQuerying(rTree, rectangles) -> list:
	rangeResults = []
	for W in rectangles:
		init_list = []
		rQuerying(rTree, W, init_list)
		rangeResults.append([W, init_list])
	return rangeResults


# make output #
def output(rangeResults, outputFp = None, encoding = "utf-8") -> bool:
	if outputFp:
		try:
			with open(outputFp, "w", encoding = encoding) as f:
				for i, result in enumerate(rangeResults):
					f.write("{0} ({1}): {2}\n".format(i, len(result[1]), ",".join([str(item) for item in result[1]])))
			print("Dump to the result file successfully. ")
			return True
		except Exception as e:
			print("Error writing output file. ")
			print(e)
			return False
	for i, result in enumerate(rangeResults):
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
		sleep(1)
		cntTime -= 1
	print("\rProgram ended, exiting in {{0:>{0}}} second(s). ".format(length).format(cntTime))

def printHelp() -> None:
	print("Python script for range querying based on RTree. ", end = "\n\n")
	print("Option: ")
	print("\t[/rTree|--rTree|rTree]: Specify that the following option is the input rTree file. ")
	print("\t[/rQueries|--rQueries|rQueries]: Specify that the following option is the input rQueries file. ")
	print("\t[/o|-o|o|/output|--output|output]: Specify that the following option is the output result file. ", end = "\n\n")
	print("Format: ")
	print("\tpython rangeQuerying.py [/rTree|--rTree|rTree] rTreeFilepath [/rQueries|--rQueries|rQueries] rQueriesFilepath [/o|-o|o|/output|--output|output] outputFilepath", end = "\n\n")
	print("Example: ")
	print("\tpython rangeQuerying.py /rTree Rtree.txt /rQueries Rqueries.txt")
	print("\tpython rangeQuerying.py /rTree Rtree.txt /rQueries Rqueries.txt /output rangeResults.txt", end = "\n\n")

def handleCommandline() -> dict:
	for arg in argv[1:]:
		if arg.lower() in ("/h", "-h", "h", "/help", "--help", "help", "/?", "-?", "?"):
			printHelp()
			return True
	if len(argv) > 1 and len(argv) not in (3, 5, 7):
		print("The count of the commandline options is incorrect. Please check your commandline. ")
		return False
	dicts = {"rTree":rTreeFilepath, "rQueries":rQueriesFilepath, "output":rangeResultsFilepath}
	pointer = None
	for arg in argv[1:]:
		if arg.lower() in ("/rtree", "--rtree", "rtree"):
			pointer = "rTree"
		elif arg.lower() in ("/rqueries", "--rqueries", "rqueries"):
			pointer = "rQueries"
		elif arg.lower() in ("/o", "-o", "o", "/output", "--output", "output"):
			pointer = "output"
		elif pointer is None:
			print("Error handling commandline, please check your commandline. ")
			return False
		else:
			dicts[pointer] = arg
			pointer = None # reset
	return dicts

def main() -> int:
	# get input #
	commandlineArgument = handleCommandline()
	if type(commandlineArgument) == bool:
		return EXIT_SUCCESS if commandlineArgument else EXIT_FAILURE
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
	queries = getQueries(commandlineArgument["rQueries"])
	if queries is None:
		print("Error reading queries, please check. ")
		preExit()
		return EXIT_FAILURE
	
	# handle queries #
	start_time = time()
	rangeResults = doRangeQuerying(rTree, queries)
	end_time = time()
	if len(queries):
		print("Total time: {0:.3f}s. Item count: {1}. Average Time: {2:.3f}ms/item. ".format(end_time - start_time, len(queries), (end_time - start_time) / len(queries) * 1000))
	else:
		print("Nothing queried since the querying list is empty. ")
	
	# make output #
	output(rangeResults, outputFp = commandlineArgument["output"])
	preExit()
	return EXIT_SUCCESS





if __name__ == "__main__":
	exit(main())