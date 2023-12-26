import os
from sys import argv, exit
from time import sleep
try:
	from numpy import array
	from matplotlib import pyplot as plt
	def plotCoords(coords, dpi  = 1200, plotFp = None) -> None:
		coords_array = array(coords)
		plt.scatter(coords_array[:, 0], coords_array[:, 1], marker = ".", color = "orange")
		plt.rcParams["figure.dpi"] = dpi
		plt.rcParams["savefig.dpi"] = dpi
		if plotFp is None:
			plt.show()
		else:
			plt.savefig(plotFp)
		plt.close()
except:
	def plotCoords(coords, dpi = 1200, plotFp = None) -> None:
		return None
try:
	os.chdir(os.path.abspath(os.path.dirname(__file__))) # cd into the location path of this script
except: # it does not work in Jupyter-notebook
	pass
EXIT_SUCCESS = 0
EXIT_FAILURE = 1
_DIVISORS = [180.0 / 2 ** n for n in range(32)]
INDICATOR = 10000
defaultTime = 5
coordsFilepath = "coords.txt"
offsetsFilepath = "offsets.txt"
rTreeFilepath = "Rtree.txt"
plotFilepath = "plot.png"


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

def getCoords(coordsFp = coordsFilepath) -> list:
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
				coords.append([float(tmp[0]), float(tmp[1])])
			except:
				print("Line {0} has been skipped since converting error occured. ".format(cnt))
		elif line: # it is not necessary to prompt the empty line
			print("Line {0} has been skipped since the count of comma(s) is not 1. ".format(cnt))
	return coords

def getOffsets(offsetsFp = offsetsFilepath) -> list:
	content = getTxt(offsetsFp)
	if content is None:
		return None
	content = content.replace("\r", "\n") # filtering "\r"
	while "\n\n" in content: # filtering empty lines
		content = content.replace("\n\n", "\n")
	offsets = []
	for cnt, line in enumerate(content.split("\n")):
		if line.count(",") == 2:
			tmp = line.split(",")
			try:
				offsets.append([int(tmp[0]), int(tmp[1]), int(tmp[2])])
			except:
				print("Line {0} has been skipped since converting error occured. ".format(cnt))
		elif line: # it is not necessary to prompt the empty line
			print("Line {0} has been skipped since the count of comma(s) is not 2. ".format(cnt))
	return offsets

def checkOffsetCoords(coords, offsets) -> bool:
	if offsets:
		for i in range(len(offsets) - 1):
			if offsets[i + 1][1] - offsets[i][2] != 1:
				print("Uncovered coords are detected: From {0} to {1}. ".format(offsets[i][2], offsets[i + 1][1]))
				return False
	else:
		return False
	if offsets[0][1] != 0:
		print("The offsets do not cover the coords as offsets begin at {0} while coords begin at 0. ".format(offsets[0][1]))
		return False
	if offsets[-1][-1] != len(coords) - 1:
		print("The offsets do not cover the coords as offsets end at {0} while coords end at {1}. ".format(offsets[-1][-1], len(coords) - 1))
		return False
	return True


# handle indexing #
def compute_mbr(coords) -> list: # find the bounds
	if coords:
		x_low = min(coords, key = lambda c:c[0])[0]
		x_high = max(coords, key = lambda c:c[0])[0]
		y_low = min(coords, key = lambda c:c[1])[1]
		y_high = max(coords, key = lambda c:c[1])[1]
		return [x_low, x_high, y_low, y_high]
	else:
		return None

def compute_geometric_center(coords) -> list: # find the geometric center
	return [sum(coord[0] for coord in coords) / len(coords), sum(coord[1] for coord in coords) / len(coords)] if coords else None

def interleave_latlng(lat, lng) -> int: # get code
	if not isinstance(lat, float) or not isinstance(lng, float):
		return None
	if lng > 180:
		x = (lng % 180) + 180.0
	elif lng < -180:
		x = (-((-lng) % 180)) + 180.0
	else:
		x = lng + 180.0
	if lat > 90:
		y = (lat % 90) + 90.0
	elif lat < -90:
		y = (-((-lat) % 90)) + 90.0
	else:
		y = lat + 90.0
	
	morton_code = ""
	for dx in _DIVISORS:
		digit = 0
		if y >= dx:
			digit |= 2
			y -= dx
		if x >= dx:
			digit |= 1
			x -= dx
		morton_code += str(digit)
	
	return int(morton_code)

def buildRTree(entries, min_capacity = 8, max_capacity = 20, level = 0, level_indicator = INDICATOR, isPrint = False) -> RTreeNode:
	if isPrint:
		print("{0} nodes at level {1}".format(len(entries), level - 1)) # last level
	if len(entries) <= max_capacity:
		print("1 node at level {0}. ".format(level)) # last level
		return RTreeNode(entries = entries, id = level * level_indicator) # root
	else:
		return buildRTree(																	\
			entries = [RTreeNode(entries = entries[i * max_capacity:(i + 1) * max_capacity], id = i + level * level_indicator) for i in range((len(entries) - 1) // max_capacity + 1)], 		\
			min_capacity = min_capacity, 															\
			max_capacity = max_capacity, 															\
			level = level + 1, 																\
			level_indicator = level_indicator, 														\
			isPrint = True																\
		)

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

def doBuildRTree(entries, min_capacity = 8, max_capacity = 20, level_indicator = INDICATOR) -> RTreeNode:
	if type(entries) != list or len(entries) < 1:
		return None
	rTree = buildRTree(entries, min_capacity = min_capacity, max_capacity = max_capacity, level_indicator = level_indicator)
	lastNode = rTree
	while isinstance(lastNode.entries[-1], RTreeNode):
		while len(lastNode.entries[-1].entries) < min_capacity:
			lastNode.entries[-1].entries.insert(0, lastNode.entries[-2].entries.pop())
		lastNode = lastNode.entries[-1]
	computeRTreeMBR(rTree)
	return rTree

def index(coords, offsets) -> list: # build index
	entries = []
	for offset in offsets:
		polygon_id, start_offset, end_offset = offset
		polygon_coords = coords[start_offset:end_offset + 1]
		mbr = compute_mbr(polygon_coords)
		center = compute_geometric_center(polygon_coords)
		if mbr is None or center is None:
			print("Warning: illegal coords[{0}:{1}] are found. ".format(start_offset, end_offset + 1))
		else:
			z_order = interleave_latlng(center[1], center[0])
			entries.append([polygon_id, mbr, z_order])
	entries.sort(key = lambda c:c[-1])
	for i in range(len(entries)): # remove z-order
		entries[i].pop()
	return doBuildRTree(entries)


# make output #
def dumpRTree(rTree, fp = None) -> None:
	for entry in rTree.entries:
		if isinstance(entry, RTreeNode):
			dumpRTree(entry, fp)
	if fp:
		fp.write("{0}\n".format(rTree))
	else:
		print(rTree)

def doDumpRTree(rTree, filepath = rTreeFilepath, encoding = "utf-8") -> bool:
	if filepath:
		try:
			with open(filepath, "w", encoding = encoding) as f:
				dumpRTree(rTree, fp = f)
			return True
		except Exception as e:
			print(e)
			return False
	else:
		dumpRTree(rTree, fp = f)



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
	print("Python script for indexing RTree. ", end = "\n\n")
	print("Option: ")
	print("\t[/coords|--coords|coords]: Specify that the following option is the input coord file. ")
	print("\t[/offsets|--offsets|offsets]: Specify that the following option is the input offset file. ")
	print("\t[/rTree|--rTree|rTree]: Specify that the following option is the output rTree file. ", end = "\n\n")
	print("Format: ")
	print("\tpython indexing.py [/coords|--coords|coords] coordsFilepath [/offsets|--offsets|offsets] offsetsFilepath [/rTree|--rTree|rTree] rTreeFilepath", end = "\n\n")
	print("Example: ")
	print("\tpython indexing.py /coords coords.txt /offsets offsets.txt")
	print("\tpython indexing.py /coords coords.txt /offsets offsets.txt /rTree Rtree.txt", end = "\n\n")

def handleCommandline() -> dict:
	for arg in argv[1:]:
		if arg.lower() in ("/h", "-h", "h", "/help", "--help", "help", "/?", "-?", "?"):
			printHelp()
			return True
	if len(argv) > 1 and len(argv) not in (3, 5, 7):
		print("The count of the commandline options is incorrect. Please check your commandline. ")
		return False
	dicts = {"coords":coordsFilepath, "offsets":offsetsFilepath, "rTree":rTreeFilepath}
	pointer = None
	for arg in argv[1:]:
		if arg.lower() in ("/coords", "--coords", "coords"):
			pointer = "coords"
		elif arg.lower() in ("/offsets", "--offsets", "offsets"):
			pointer = "offsets"
		elif arg.lower() in ("/rtree", "--rtree", "rtree"):
			pointer = "rTree"
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
	coords = getCoords(commandlineArgument["coords"])
	if coords is None:
		print("Error reading coords, please check. ")
		preExit()
		return EXIT_FAILURE
	offsets = getOffsets(commandlineArgument["offsets"])
	if offsets is None:
		print("Error reading offsets, please check. ")
		preExit()
		return EXIT_FAILURE
	if not checkOffsetCoords(coords, offsets):
		preExit()
		return EXIT_FAILURE
	plotCoords(coords, plotFp = plotFilepath)
	
	# handle indexing #
	rTree = index(coords, offsets)
	
	# make output #
	doDumpRTree(rTree, filepath = commandlineArgument["rTree"])
	preExit()
	return EXIT_SUCCESS





if __name__ == "__main__":
	exit(main())