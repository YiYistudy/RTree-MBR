import os
from sys import argv, exit
from time import sleep, time
try:
	os.chdir(os.path.abspath(os.path.dirname(__file__))) # cd into the location path of this script
except: # it does not work in Jupyter-notebook
	pass
EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EOF = (-1)
global_offsets = {} # to speed up
defaultTime = 5
defaultGrid = 100
coordsFilepath = "coords.txt"
gridQueriesFilepath = "NNqueries.txt"
gridResultsFilepath = "gridResults.txt"


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

def getQueries(gridQueriesFp = gridQueriesFilepath) -> list:
	content = getTxt(gridQueriesFp)
	if content is None:
		return None
	content = content.replace("\r", "\n") # filtering "\r"
	while "\n\n" in content: # filtering empty lines
		content = content.replace("\n\n", "\n")
	queries = []
	for cnt, line in enumerate(content.split("\n")):
		if line.count(" ") == 1:
			tmp = line.split(" ")
			try:
				queries.append([float(tmp[0]), float(tmp[1])])
			except:
				print("Line {0} has been skipped since converting error occured. ".format(cnt))
		elif line: # it is not necessary to prompt the empty line
			print("Line {0} has been skipped since the count of space(s) is not 1. ".format(cnt))
	return queries


# build grid #
def computeBoundary(coords) -> list: # find the bounds
	if coords:
		x_low = min(coords, key = lambda c:c[0])[0]
		x_high = max(coords, key = lambda c:c[0])[0]
		y_low = min(coords, key = lambda c:c[1])[1]
		y_high = max(coords, key = lambda c:c[1])[1]
		return [x_low, x_high, y_low, y_high]
	else:
		return None

def buildGrid(coords, gridCnt = defaultGrid) -> dict:
	boundary = computeBoundary(coords) # [x_low, x_high, y_low, y_high]
	if boundary is None:
		return None
	x_low, x_high, y_low, y_high = boundary[0], boundary[1], boundary[2], boundary[3]
	x_distance = (x_high - x_low) / gridCnt
	y_distance = (y_high - y_low) / gridCnt
	gridDicts = {				\
		"x_low":x_low, 			\
		"x_high":x_high, 			\
		"y_low":y_low, 			\
		"y_high":y_high, 			\
		"x_distance":x_distance, 		\
		"y_distance":y_distance, 		\
		"gridCount":gridCnt, 			\
		"pointCnt":len(coords)		\
	}
	for coord in coords:
		x_index = gridCnt - 1 if coord[0] == x_high else int((coord[0] - x_low) // x_distance)
		y_index = gridCnt - 1 if coord[1] == y_high else int((coord[1] - y_low) // y_distance)
		gridDicts.setdefault((x_index, y_index), [])
		gridDicts[(x_index, y_index)].append(coord)
	return gridDicts


# handle queries #
def getCellFromLocation(location, gridDicts) -> tuple:
	if gridDicts["x_low"] <= location[0] <= gridDicts["x_high"] and gridDicts["y_low"] <= location[1] <= gridDicts["y_high"]:
		return (															\
			gridDicts["gridCount"] - 1 if location[0] == gridDicts["x_high"] else int((location[0] - gridDicts["x_low"]) // gridDicts["x_distance"]), 		\
			gridDicts["gridCount"] - 1 if location[1] == gridDicts["y_high"] else int((location[1] - gridDicts["y_low"])  // gridDicts["y_distance"])		\
		)
	else:
		return None

def getLocationsFromCell(cell, gridDicts) -> list:
	return [									\
		cell[0] * gridDicts["x_distance"] + gridDicts["x_low"], 			\
		(cell[0] + 1) * gridDicts["x_distance"] + gridDicts["x_low"], 		\
		cell[1] * gridDicts["x_distance"] + gridDicts["y_low"], 			\
		(cell[1] + 1) * gridDicts["y_distance"] + gridDicts["y_low"]			\
	]

def distance(rectangle, q) -> float:
	x_distance = 0 if rectangle[0] <= q[0] <= rectangle[1] else min(abs(rectangle[0] - q[0]), abs(rectangle[1] - q[0]))
	y_distance = 0 if rectangle[2] <= q[1] <= rectangle[3] else min(abs(rectangle[2] - q[1]), abs(rectangle[3] - q[1]))
	return (x_distance ** 2 + y_distance ** 2) ** (1 / 2)

def doGridSearching(gridDicts, queries, k) -> list:
	gridResults = []
	for q in queries:
		idx = getCellFromLocation(q, gridDicts)
		if idx is None:
			continue
		results = []
		for coord in gridDicts[idx]:
			results.append((((coord[0] - q[0]) ** 2 + (coord[1] - q[1]) ** 2) ** (1 / 2), coord))
		results = sorted(results, key = lambda c:c[0])[:k]
		depth = 0
		max_depth = max(idx[0], gridDicts["gridCount"] - idx[0], idx[1], gridDicts["gridCount"] - idx[1])
		while depth < max_depth:
			depth += 1
			if depth not in global_offsets: # to speed up
				global_offsets[depth] = [(-depth, j) for j in range(-depth, depth)] + [(i, depth) for i in range(-depth, depth)] + [(depth, j) for j in range(depth, -depth, -1)] + [(i, -depth) for i in range(depth, -depth, -1)]
			offsets = [(idx[0] + offset[0], idx[1] + offset[1]) for offset in global_offsets[depth]]
			for i in range(len(offsets) - 1, -1, -1): # remove invalid elements from back to front
				if offsets[i][0] < 0 or offsets[i][0] >= gridDicts["gridCount"] and offsets[i][1] < 0 or offsets[i][1] >= gridDicts["gridCount"]:
					del offsets[i]
			flags = []
			for cell in offsets:
				loc = getLocationsFromCell(cell, gridDicts)
				if len(results) < k: # not enough
					flags.append(True) # cannot be pruned
					for coord in gridDicts[cell]: # add no matter how large it is since no adequate items in the list
						results.append((((coord[0] - q[0]) ** 2 + (coord[1] - q[1]) ** 2) ** (1 / 2), coord))
					results = sorted(results, key = lambda c:c[0])[:k]
				else: # require update
					d = distance(loc, q)
					if d >= results[-1][0]: # no nearer points in the cell since the distance to cell is not smaller than t
						flags.append(False) # ignore the cell
					else: # prune
						flags.append(True) # this layer cannot be pruned
						for coord in gridDicts[cell]:
							results.append((((coord[0] - q[0]) ** 2 + (coord[1] - q[1]) ** 2) ** (1 / 2), coord))
						results = sorted(results, key = lambda c:c[0])[:k]
				if not any(flags): # Finished
					break
		gridResults.append([q, [coord[1][2] for coord in results]]) # only record ID
	return gridResults


# make output #
def output(gridResults, outputFp = None, encoding = "utf-8") -> bool:
	if outputFp:
		try:
			with open(outputFp, "w", encoding = encoding) as f:
				for i, result in enumerate(gridResults):
					f.write("{0} ({1}): {2}\n".format(i, len(result[1]), ",".join([str(item) for item in result[1]])))
			print("Dump to the result file successfully. ")
			return True
		except Exception as e:
			print("Error writing output file. ")
			print(e)
			return False
	for i, result in enumerate(gridResults):
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
	print("Python script for Grid querying based on RTree. ", end = "\n\n")
	print("Option: ")
	print("\t[/coords|--coords|coords]: Specify that the following option is the input coord file. ")
	print("\t[/g|-g|g|/grid|--grid|grid]: Specify that the following option is the input grid (g). ")
	print("\t[/gridQueries|--gridQueries|gridQueries]: Specify that the following option is the input Grid querying file. ")
	print("\t[/k|-k|k]: Specify that the following option is the input k. ")
	print("\t[/o|-o|o|/output|--output|output]: Specify that the following option is the output result file. ", end = "\n\n")
	print("Format: ")
	print("\tpython gridSearching.py [/coords|--coords|coords] coordsFilepath [/g|-g|g|/grid|--grid|grid] grid [/gridQueries|--gridQueries|gridQueries] gridQueriesFilepath [/k|-k|k] k [/o|-o|o|/output|--output|output] outputFilepath", end = "\n\n")
	print("Example: ")
	print("\tpython gridSearching.py /coords coords.txt /g 100 /gridQueries NNqueries.txt /k 10")
	print("\tpython gridSearching.py /coords coords.txt /g 100 /gridQueries NNqueries.txt /k 10 /output gridResults.txt", end = "\n\n")

def handleCommandline() -> dict:
	for arg in argv[1:]:
		if arg.lower() in ("/h", "-h", "h", "/help", "--help", "help", "/?", "-?", "?"):
			printHelp()
			return True
	if len(argv) > 1 and len(argv) not in (3, 5, 7, 9, 11):
		print("The count of the commandline options is incorrect. Please check your commandline. ")
		return False
	dicts = {"coords":coordsFilepath, "grid":defaultGrid, "gridQueries":gridQueriesFilepath, "k":10, "output":gridResultsFilepath}
	pointer = None
	for arg in argv[1:]:
		if arg.lower() in ("/coords", "--coords", "coords"):
			pointer = "coords"
		elif arg.lower() in ("/g", "-g", "g", "/grid", "--grid", "grid"):
			pointer = "grid"
		elif arg.lower() in ("/gridqueries", "--gridqueries", "gridqueries"):
			pointer = "gridQueries"
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
		dicts["grid"] = int(dicts["grid"])
		dicts["k"] = int(dicts["k"])
		if dicts["grid"] < 1 or dicts["k"] < 1:
			raise ValueError("Both the gird and the k should be larger than 0. ")
	except:
		print("Error regarding grid or k as an integer. Please check your commandline. ")
		return False
	return dicts

def main() -> int:
	# get input #
	commandlineArgument = handleCommandline()
	if type(commandlineArgument) == bool:
		return EXIT_SUCCESS if commandlineArgument else EXIT_FAILURE
	coords = getCoordsWithID(commandlineArgument["coords"])
	if coords is None:
		print("Error reading coords, please check. ")
		preExit()
		return EXIT_FAILURE
	queries = getQueries(commandlineArgument["gridQueries"])
	if queries is None:
		print("Error reading queries, please check. ")
		preExit()
		return EXIT_FAILURE
	
	# build grid #
	gridDicts = buildGrid(coords, commandlineArgument["grid"])
	
	# handle queries #
	start_time = time()
	gridResults = doGridSearching(gridDicts, queries, commandlineArgument["k"])
	end_time = time()
	if len(queries):
		print("Total time: {0:.3f}s. Item count: {1}. Average Time: {2:.3f}ms/item. ".format(end_time - start_time, len(queries), (end_time - start_time) / len(queries) * 1000))
	else:
		print("Nothing queried since the querying list is empty. ")
	
	# make output #
	output(gridResults, outputFp = commandlineArgument["output"])
	preExit()
	return EXIT_SUCCESS





if __name__ == "__main__":
	exit(main())