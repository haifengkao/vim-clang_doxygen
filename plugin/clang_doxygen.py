# Vim plugin for generating Doxygen comments
# Last Change:  2013 Jan 24
# Maintainer:   Sven Strothoff <sven.strothoff@googlemail.com>
# License:      See documentation (clang_doxygen.txt)
# 
# Copyright (c) 2013, Sven Strothoff
# All rights reserved.

import vim
import re
from clang.cindex import Index, SourceLocation, Cursor, File, CursorKind, TypeKind, Config, LibclangError

# Generate doxygen comments for a class declaration.
def handleClassDecl(c):
  tabStopCounter = 1
  doxygenLines = []
  className = c.spelling

  # Class name
  if vim.eval("g:clang_doxygen_use_block") == "1":
    if vim.eval("g:clang_doxygen_block_no_newline") == "1":
      doxygenLines.append(vim.eval("g:clang_doxygen_block_start"))
    else:
      doxygenLines.append(vim.eval("g:clang_doxygen_block_start"))
      doxygenLines.append(vim.eval("g:clang_doxygen_comment_middle"))
  else:
    doxygenLines.append(vim.eval("g:clang_doxygen_comment_middle"))

  doxygenLines[-1] += vim.eval("g:clang_doxygen_tag_brief") + "${" + str(tabStopCounter) + ":" + className + "}"
  tabStopCounter += 1
  doxygenLines.append(vim.eval("g:clang_doxygen_comment_middle"))
  doxygenLines.append(vim.eval("g:clang_doxygen_comment_middle") + "$0")

  # Close block comment
  if vim.eval("g:clang_doxygen_use_block") == "1":
    doxygenLines.append(vim.eval("g:clang_doxygen_block_end"))

  # Add indentation.
  # Comment indentation should match the indentation of the line containing the
  # declaration name, however clang_getSpellingLocation() ist note exposed by
  # the Python bindings.
  tabCount = vim.current.buffer[c.location.line - 1][:c.location.column - 1].count('\t')
  indent = (c.extent.start.column - 1 - tabCount) + tabCount * int(vim.eval("&tabstop"))
  indentString = indent * " "
  for l in xrange(0, len(doxygenLines)):
    doxygenLines[l] = indentString + doxygenLines[l]

  return (c.extent.start.line, doxygenLines)

# Generate doxygen comments for a function declaration.
def handleFunctionDecl(c):
  tabStopCounter = 1
  doxygenLines = []
  functionName = c.spelling

  # Function name
  if vim.eval("g:clang_doxygen_use_block") == "1":
    if vim.eval("g:clang_doxygen_block_no_newline") == "1":
      doxygenLines.append(vim.eval("g:clang_doxygen_block_start"))
    else:
      doxygenLines.append(vim.eval("g:clang_doxygen_block_start"))
      doxygenLines.append(vim.eval("g:clang_doxygen_comment_middle"))
  else:
    doxygenLines.append(vim.eval("g:clang_doxygen_comment_middle"))

  doxygenLines[-1] += vim.eval("g:clang_doxygen_tag_brief") + "${" + str(tabStopCounter) + ":" + functionName + "}"
  tabStopCounter += 1
  doxygenLines.append(vim.eval("g:clang_doxygen_comment_middle"))
  doxygenLines.append(vim.eval("g:clang_doxygen_comment_middle") + "$0")

  # Extract parameters.
  # Only supported by libClang >= 3.1
  #n = c.get_num_arguments()
  #for i in xrange(0, n):
  #  print "  Argument: %s" % c.get_argument(i).spelling
  paramLines = []
  children = c.get_children()
  for arg in children:
    if arg.kind != CursorKind.PARM_DECL:
      continue
    paramLines.append(vim.eval("g:clang_doxygen_comment_middle") + vim.eval("g:clang_doxygen_tag_param") + arg.spelling + " ${" + str(tabStopCounter) + ":" + arg.spelling + "}")
    tabStopCounter += 1
  if len(paramLines) > 0:
    doxygenLines.append(vim.eval("g:clang_doxygen_comment_middle"))
  doxygenLines += paramLines

  # Check result type.
  if c.type.get_result().kind != TypeKind.VOID:
    doxygenLines.append(vim.eval("g:clang_doxygen_comment_middle"))
    doxygenLines.append(vim.eval("g:clang_doxygen_comment_middle") + vim.eval("g:clang_doxygen_tag_return") + "${" + str(tabStopCounter) + ":" + c.type.get_result().kind.spelling + "}")
    tabStopCounter += 1

  # Close block comment
  if vim.eval("g:clang_doxygen_use_block") == "1":
    doxygenLines.append(vim.eval("g:clang_doxygen_block_end"))

  # Add indentation.
  # Comment indentation should match the indentation of the line containing the
  # declaration name, however clang_getSpellingLocation() ist note exposed by
  # the Python bindings.
  tabCount = vim.current.buffer[c.location.line - 1][:c.location.column - 1].count('\t')
  indent = (c.extent.start.column - 1 - tabCount) + tabCount * int(vim.eval("&tabstop"))
  indentString = indent * " "
  for l in xrange(0, len(doxygenLines)):
    doxygenLines[l] = indentString + doxygenLines[l]

  return (c.extent.start.line, doxygenLines)

# Return buffer contents between the specified source locations. Returns lines
# in an array.
def getBufferContent(startLine, startCol, endLine, endCol):
  resultLines = vim.current.buffer[startLine - 1:endLine]
  if startLine == endLine:
    resultLines[0] = resultLines[0][startCol - 1:endCol]
  else:
    resultLines[0] = resultLines[0][startCol - 1:]
    resultLines[-1] = resultLines[-1][:endCol]
  return resultLines

# Generate doxygen comments for a function template.
def handleFunctionTemplate(c):
  tabStopCounter = 1
  doxygenLines = []
  functionName = c.spelling
  doxygenLines.append("/// \\brief ${" + str(tabStopCounter) + ":" + functionName + "}")
  tabStopCounter += 1
  doxygenLines.append("/// ")
  doxygenLines.append("/// $0")

  # Extract parameters.
  paramLines = []
  children = c.get_children()
  for arg in children:
    if arg.kind != CursorKind.PARM_DECL:
      continue
    paramLines.append("/// \\param " + arg.spelling + " ${" + str(tabStopCounter) + ":" + arg.spelling + "}")
    tabStopCounter += 1
  if len(paramLines) > 0:
    doxygenLines.append("/// ")
  doxygenLines += paramLines

  # Find TemplateTypeParameter to determine result type.
  templateTypeParameterCursor = None
  for child in c.get_children():
    if child.kind == CursorKind.TEMPLATE_TYPE_PARAMETER:
      templateTypeParameterCursor = child
      break
  if templateTypeParameterCursor is None:
    print "Unable to find TemplateTypeParameter."
    return (None, None)
  
  # Get result type string(s).
  startLine = templateTypeParameterCursor.extent.end.line
  startCol = templateTypeParameterCursor.extent.end.column + 1
  endLine, endCol = previousSourceLocation(c.location.line, c.location.column)
  resultLines = getBufferContent(startLine, startCol, endLine, endCol)

  # Check if the result type is void; if not extract result type string.
  blockCommentRegex = re.compile(r"/\*.*?\*/", re.DOTALL)
  resultString = re.sub(blockCommentRegex, "", "\n".join(resultLines))
  if re.search(r"void", resultString) is None:
    doxygenLines.append("/// ")
    doxygenLines.append("/// \\return ${" + str(tabStopCounter) + ":" + c.type.get_result().kind.spelling + "}")
    tabStopCounter += 1

  # Add indentation.
  # Comment indentation should match the indentation of the line containing the
  # declaration name, however clang_getSpellingLocation() ist note exposed by
  # the Python bindings.
  tabCount = vim.current.buffer[c.location.line - 1][:c.location.column - 1].count('\t')
  indent = (c.extent.start.column - 1 - tabCount) + tabCount * int(vim.eval("&tabstop"))
  indentString = indent * " "
  for l in xrange(0, len(doxygenLines)):
    doxygenLines[l] = indentString + doxygenLines[l]

  return (c.extent.start.line, doxygenLines)

# Returns the previous source location or None if already at the beginning of
# the buffer.
def previousSourceLocation(line, col):
  if col > 1:
    return (line, col - 1)
  if line == 1:
    return None
  return (line - 1, len(vim.current.buffer[line - 2]))

# Returns the next source location or None if already at the end of
# the buffer.
def nextSourceLocation(line, col):
  if col < len(vim.current.buffer[line - 1]):
    return (line, col + 1)
  if line == len(vim.current.buffer):
    return None
  return (line + 1, 1)

# Generate doxygen for declaration at specified source location.
# Returns a tuple consisting of the line number at which the doxygen comment
# should be inserted and the doxygen comment as an array (one line per element).
def generateDoxygenForSourceLocation(line, col):
  filename = vim.current.buffer.name

  index = Index.create()
  tu = index.parse(filename, vim.eval("g:clang_doxygen_clang_args"), [(filename, "\n".join(vim.current.buffer[:]))])

  # Skip whitespace at beginning of line
  indent = re.match(r'^\s*', vim.current.buffer[line - 1]).span()[1]
  col = max(col, indent + 1)

  c = Cursor.from_location(tu, SourceLocation.from_position(tu, File.from_name(tu, filename), line, col))

  # If there is no declaration at the source location try to find the nearest one.
  while c is not None:
    # If cursor is on a TypeRef in a FunctionTemplate, manually go backward in the source.
    if c.kind == CursorKind.TYPE_REF:
      pLine, pCol = previousSourceLocation(c.extent.start.line, c.extent.start.column)
      c = Cursor.from_location(tu, SourceLocation.from_position(tu, File.from_name(tu, filename), pLine, pCol))
      continue
    # If cursor is on a NamespaceRef, manually go forward in the source.
    elif c.kind == CursorKind.NAMESPACE_REF:
      nLine, nCol = nextSourceLocation(c.extent.end.line, c.extent.end.column)
      c = Cursor.from_location(tu, SourceLocation.from_position(tu, File.from_name(tu, filename), nLine, nCol))
      continue
    elif c.kind == CursorKind.FUNCTION_DECL:
      return handleFunctionDecl(c)
    elif c.kind == CursorKind.CXX_METHOD:
      return handleFunctionDecl(c)
    elif c.kind == CursorKind.CONSTRUCTOR:
      return handleFunctionDecl(c)
    elif c.kind == CursorKind.DESTRUCTOR:
      return handleFunctionDecl(c)
    elif c.kind == CursorKind.FUNCTION_TEMPLATE:
      return handleFunctionTemplate(c)
    elif c.kind == CursorKind.CLASS_DECL:
      return handleClassDecl(c)
    elif c.kind == CursorKind.CLASS_TEMPLATE:
      return handleClassDecl(c)
    elif c.kind == CursorKind.OBJC_INSTANCE_METHOD_DECL:
      return handleFunctionDecl(c)
    elif c.kind == CursorKind.OBJC_INTERFACE_DECL:
      return handleClassDecl(c)
    elif c.kind == CursorKind.OBJC_CATEGORY_DECL:
      return handleClassDecl(c)
    elif c.kind == CursorKind.OBJC_IMPLEMENTATION_DECL:
      return handleClassDecl(c)
    # Cursor is not on a supported type, go to the lexical parent
    else:
      c = c.lexical_parent

  if c is None:
    print "Error: No supported declaration found at %s:%i,%i.\n" % (filename, line, col)
    return (None, None)

# Generate Doxygen comments for the current source location.
def generateDoxygen():
  # First line is 1, first column is 0
  (line, col) = vim.current.window.cursor

  (insertLine, doxygenLines) = generateDoxygenForSourceLocation(line, col + 1)
  if doxygenLines is None:
    return
  vim.current.buffer.append("", insertLine - 1)
  vim.current.window.cursor = (insertLine, 0)
  # Call snippet plugin
  vim.command('call clang_doxygen_snippets#' + vim.eval("g:clang_doxygen_snippet_plugin") + '#trigger(\'' + "\n".join(doxygenLines).replace("\\", "\\\\") + '\')')

# Try to find liblang. Set library path if necessary.
def initialiseClangDoxygen():
  conf = Config()

  if vim.eval("exists(\"g:clang_doxygen_libclang_library_path\")") != "0":
    Config.set_library_path(vim.eval("g:clang_doxygen_libclang_library_path"))
    conf.set_library_path(vim.eval("g:clang_doxygen_libclang_library_path"))

  try:
    conf.get_cindex_library()
  except LibclangError as e:
    print "Error: " + str(e)
    return

  vim.command("let g:initialised_clang_doxygen = 1")
