#!/usr/bin/env python
# -*- coding: utf-8  -*-
"""
=========================================================================
        msproteomicstools -- Mass Spectrometry Proteomics Tools
=========================================================================

Copyright (c) 2013, ETH Zurich
For a full list of authors, refer to the file AUTHORS.

This software is released under a three-clause BSD license:
 * Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.
 * Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.
 * Neither the name of any author or any participating institution
   may be used to endorse or promote products derived from this software
   without specific prior written permission.
--------------------------------------------------------------------------
THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL ANY OF THE AUTHORS OR THE CONTRIBUTING
INSTITUTIONS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
--------------------------------------------------------------------------
$Maintainer: Hannes Roest$
$Authors: Hannes Roest$
--------------------------------------------------------------------------
"""

# https://pypi.python.org/pypi/breathe
# $ sudo pip install breathe

import glob, os, sys
import argparse
import re
from PythonCheckerLib import parse_pxd_file
from PythonCheckerLib import create_pxd_file_map
import breathe.parser
from breathe.parser.doxygen.compound import parse as doxygen_parse
from Cython.Compiler.Nodes import CEnumDefNode, CppClassNode, CTypeDefNode, CVarDefNode, CImportStatNode, CDefExternNode
from autowrap.PXDParser import CppClassDecl, CTypeDefDecl, MethodOrAttributeDecl, EnumDecl
import yaml

class Counter(object):
    def __init__(self):
        self.total = 0
        self.skipped = 0
        self.skipped_could_not_parse = 0
        self.skipped_protected = 0
        self.skipped_no_location = 0
        self.skipped_no_sections = 0
        self.skipped_no_pxd_file = 0
        self.skipped_no_pxd_match = 0
        self.parsed = 0
        # 
        self.public_enums_total = 0
        self.public_enums_missing = 0
        # 
        self.public_methods = 0
        self.public_methods_missing = 0
        self.public_methods_missing_nowrapping = 0
        self.public_variables = 0
        self.public_variables_missing = 0

    def print_skipping_reason(self):
        self.skipped = self.skipped_could_not_parse + self.skipped_no_location + self.skipped_no_sections + self.skipped_no_pxd_file + self.skipped_no_pxd_match  
        print "Skipped files: %s" % self.skipped
        print "- Could not parse xml: %s" % self.skipped_could_not_parse
        print "- Could not parse location in xml: %s" % self.skipped_no_location
        print "- Protected Compound: %s" % self.skipped_protected
        print "- Could not find sections in xml: %s" % self.skipped_no_sections
        print "- Could not find associated pxd file : %s" % self.skipped_no_pxd_file
        print "- Could not find matching class in pxd file : %s" % self.skipped_no_pxd_match

    def print_stats(self):
        self.skipped = self.skipped_could_not_parse + self.skipped_no_location + self.skipped_no_sections + self.skipped_no_pxd_file + self.skipped_no_pxd_match + self.skipped_protected
        print "Total files: %s" % self.total
        print "Skipped files: %s" % self.skipped
        print "Parsed files: %s" % self.parsed
        print "Parsed public methods %s (of which were missing %s and %s were operator/destructors) " % (self.public_methods, self.public_methods_missing, self.public_methods_missing_nowrapping)
        print "  - wrapped %s " % (self.public_methods - self.public_methods_missing)
        print "  - unwrapped operators/destructors %s " % (self.public_methods_missing_nowrapping)
        print "  - unwrapped methods %s " % (self.public_methods_missing - self.public_methods_missing_nowrapping)
        print "Parsed public enums %s (of which were missing %s) " % (self.public_enums_total, self.public_enums_missing)
        print "Parsed public attributes %s (of which were missing %s) " % (self.public_variables, self.public_variables_missing)
        print "Note that this script counts each method name only once and only maps from \n"+ \
              "C++ to Python (not the other way around), thus the numbers are slightly inaccurate." 

def handle_member_definition(mdef, cnt, cl):
    protection = mdef.get_prot() # DoxProtectionKind: public, protected, private, package
    kind = mdef.get_kind() # DoxMemberKind: define property event variable typedef enum function signal prototype friend dcop slot 
    if not protection in "public protected private package".split(" "):
        raise Exception("Error; something is wrong")
    if not kind in "define property event variable typedef enum function signal prototype friend dcop slot".split(" "):
        raise Exception("Error; something is wrong")
    if kind == "enum" and protection == "public":
        cnt.public_enums_total += 1
        cython_file = parse_pxd_file(cl.pxd_path)
        found = False
        for klass in cython_file:
            if hasattr(klass[0], "name") and klass[0].name == mdef.get_name():
                found = True
                break
        if not found:
            print "TODO: Found enum in C++ but not in pxd: ", mdef.kind,  mdef.prot, mdef.name
            cnt.public_enums_missing += 1
        elif len(klass[0].items) != len(mdef.get_enumvalue()):
            print "TODO: Found enum in C++ with %s members but in Cython there are %s members: " % (
                len(mdef.get_enumvalue()), len(klass[0].items) )
    elif kind == "variable" and protection == "public":
        attrnames = [a.name for a in cl.attributes]
        cnt.public_variables += 1
        if not mdef.name in attrnames:
            print "TODO: Found attribute in cpp but not in pxd: ", mdef.kind,  mdef.prot, mdef.name
            cnt.public_variables_missing += 1
    elif kind == "function" and protection == "public":
        # Wrap of public member functions ... 
        cnt.public_methods += 1
        c_return_type = CppFunctionDefinition().resolve_return_type(mdef)
        if mdef.name in cl.methods:
            # Found match between C++ method and Python method
            py_methods = cl.methods[mdef.name]
            if not isinstance(py_methods, list):
                py_methods = [py_methods]
            py_return_type = [str(d.result_type) for d in py_methods]
            if mdef.definition == mdef.name:
                # Constructor, no return type
                assert len(c_return_type) == 0
            elif "void" in py_return_type and not "void" in c_return_type:
                print "TODO: Mismatch between C++ return type (%s) and Python return type (%s) in %s %s %s:" % ( 
                     str(c_return_type), str(py_return_type), mdef.kind,  mdef.prot, mdef.name)
        else:
            cnt.public_methods_missing += 1
            if mdef.name.find("~") != -1:
                # destructor
                cnt.public_methods_missing_nowrapping += 1
            elif (mdef.name.find("operator") != -1 or
                  mdef.name.find("begin") != -1 or
                  mdef.name.find("end") != -1):
                cnt.public_methods_missing_nowrapping += 1
            else:
                print " -- TODO missing function in PXD: ", CppFunctionDefinition().format_definition_for_cython(mdef)

class OpenMSSourceFile(object):
    def __init__(self, fname):
        self.fname = fname

    def getMaintainer(self):
        try:
            return self._getMaintainer()
        except IOError:
            return None

    def _getMaintainer(self):
        """
        // $Maintainer: xxx $
        // $Authors: xxx $
        """
        maintainer_reg = re.compile(".*\$\s*Maintainer:([^\$]*)\$")
        with open(self.fname) as f:
            data = f.read()
            maintainer = maintainer_reg.search(data)
            if maintainer is not None:
                return maintainer.group(1).strip()
            else:
                return None


#
## Class holding Doxygen XML file and next one function declaration
# 
class DoxygenXMLFile(object):
    """The doxygen XML file
    """

    def __init__(self, fname):
        self.fname = fname
        self.parsed_file = None
        self.parsing_error = False

    def parse(self):
        try:
            self.parsed_file =  doxygen_parse(self.fname)
            return self.parsed_file
        except Exception as e:
            print "Error parsing doxygen xml file", e.message
            self.parsing_error = True
            return None

    def getCompoundFileLocation(self):
        location = self.parsed_file.get_compounddef().get_location() 
        if location is None:
            return None
        return os.path.realpath(location.get_file())

    def empty(self, discard_defines=False):
        compound = self.parsed_file.get_compounddef()
        if not discard_defines:
            return len(compound.get_sectiondef()) == 0

        # check whether there is more than defines and typdefs
        empty = True
        for sdef in compound.get_sectiondef():
            for mdef in sdef.get_memberdef():
                if not mdef.get_kind() in ["define", "typedef"]:
                    # DoxMemberKind: define property event variable typedef enum function signal prototype friend dcop slot 
                    empty = False
        if empty and not len(compound.get_sectiondef()) == 0:
            print  "== contains only typedefs etc", self.fname
        return empty

    def get_pxd_from_class(self, compound, file_location, xml_output_path):
        comp_name = compound.get_compoundname()
        #
        # Step 1: print includes
        # 
        includes = ""
        if len(compound.get_includes()) == 1:
            try:
                reffile = xml_output_path + compound.get_includes()[0].get_refid() + ".xml"
                # read includes from ref file
                dreffile = DoxygenXMLFile(reffile).parse()
                include_compound = dreffile.get_compounddef()
            except Exception as e:
                include_compound = compound
        else:
            include_compound = compound

        for inc in include_compound.get_includes():
            val = inc.getValueOf_()
            if val.startswith("OpenMS"):
                header_file = val.split("/")[-1]
                if header_file.endswith(".h"):
                    header_file = header_file[:-2]
                # We do not import certain headers since we did not wrap them in Python
                if header_file in ["Exception", "Macros", "config", "StandardTypes"]:
                    continue
                includes += "from %s cimport *\n" % header_file
        # print extern definition
        # print file_location
        if len(file_location.split("/include/OpenMS")) != 2:
            return None
        #
        # Step 2: class definition
        # 
        internal_file_name = "OpenMS" + file_location.split("/include/OpenMS")[1]
        namespace = "::".join(comp_name.split("::")[:-1])
        preferred_classname = "_".join(comp_name.split("::")[1:])
        cldef  = "\n"
        cldef += 'cdef extern from "<%s>" namespace "%s":\n' % (internal_file_name, namespace)
        cldef += "    \n"
        cldef += '    cdef cppclass %s "%s":\n' % (preferred_classname, comp_name)
        methods = ""
        #
        # Step 3: methods
        # 
        default_ctor = False
        copy_ctor = False
        enum = ""
        imports_needed = {}
        for sdef in compound.get_sectiondef():
            # break
            for mdef in sdef.get_memberdef():
                if mdef.kind == "enum" and mdef.prot == "public":
                    # add enums
                    enum += '\n'
                    enum += 'cdef extern from "<%s>" namespace "%s":\n' % (internal_file_name, comp_name)
                    enum += '    cdef enum %s "%s":\n' % (mdef.name, comp_name + "::" + mdef.name)
                    enum += '        #wrap-attach:\n'
                    enum += '        #    %s\n' % preferred_classname
                    for val in mdef.enumvalue:
                        enum += '        %s\n' % val.get_name()

                if mdef.kind == "variable" and mdef.prot == "public":
                    # print "var", mdef.name
                    methods += "        %s\n" % CppFunctionDefinition().format_definition_for_cython(mdef, False)
                elif mdef.kind == "function" and mdef.prot == "public":
                    if mdef.definition == mdef.name:
                        # print "we have a constructor", mdef.name, mdef.get_argsstring()
                        if mdef.get_argsstring().strip() == "()":
                            # print "have default"
                            default_ctor = True
                            continue
                        elif mdef.get_argsstring().strip().find(mdef.name) != -1 and \
                             mdef.get_argsstring().strip().find(",") == -1:
                            # print "have copy"
                            copy_ctor = True
                            continue
                    if mdef.name.find("~") != -1:
                        # print "we have a deconstructor", mdef.name
                        continue
                    # res += "do member function/attribute : ", mdef.kind,  mdef.prot, mdef.name
                    declaration = CppFunctionDefinition().format_definition_for_cython(mdef, False)
                    CppFunctionDefinition().compute_imports(declaration, imports_needed)
                    if declaration.find("operator=(") != -1:
                        # assignment operator, cannot be overriden in Python
                        continue
                    methods += "        %s nogil except +\n" % declaration

        # Add the imports we need
        res  = CppFunctionDefinition().generate_imports(imports_needed)
        res += includes
        res += cldef
        if default_ctor:
            res += "        %s() nogil except +\n" % comp_name.split("::")[-1]
        if not copy_ctor:
            res += "        %s(%s) nogil except + #wrap-ignore\n" % (comp_name.split("::")[-1], comp_name.split("::")[-1])
        else:
            res += "        %s(%s) nogil except +\n" % (comp_name.split("::")[-1], comp_name.split("::")[-1])
        res += methods
        res += enum
        res += "\n"
        return res

class CppFunctionDefinition(object):
    """ A Cpp function definition from a doxygen file"""
    def __init__(self):
        pass

    def resolve_return_type(self, mdef):
        res = []
        for c in mdef.get_type().content_:
            val = c.getValue()
            if hasattr(val, "getValueOf_"):
                res.append(val.getValueOf_())
            else:
                res.append(val)
        return res

    def generate_imports(self, imports):
        res = ""
        for k in sorted(imports.keys()):
            if k == "bool":
                res += "from libcpp cimport bool\n"
            else:
                res += "from libcpp.%s cimport %s as libcpp_%s\n" % (k,k,k)
        return res

    def compute_imports(self, declaration, imports):
        if declaration.find("libcpp_vector") != -1:
            imports["vector"] = 0
        if declaration.find("libcpp_pair") != -1:
            imports["pair"] = 0
        if declaration.find("libcpp_map") != -1:
            imports["map"] = 0
        if declaration.find("libcpp_set") != -1:
            imports["set"] = 0
        if declaration.find("libcpp_string") != -1:
            imports["string"] = 0
        if declaration.find("bool") != -1:
            imports["bool"] = 0

    def format_definition_for_cython(self, mdef, replace_nogil=True):
        c_return_type = self.resolve_return_type(mdef)

        # remove default arguments, Cython doesnt like them
        arguments = re.sub("\=[^,\)]*", "", mdef.get_argsstring())
        function_name = mdef.name

        # remove returned references
        return_type = "".join(c_return_type)
        return_type = return_type.replace("&", "")
        cpp_def = return_type + " " + function_name + arguments
        cpp_def = cpp_def.replace("///", "#")    
        cpp_def = cpp_def.replace("//", "#")    
        if replace_nogil:
            cpp_def = cpp_def.replace(";", "nogil except +")    
            cpp_def = cpp_def.replace("const;", "nogil except +")    
        else:
            cpp_def = cpp_def.replace("const;", "")
            cpp_def = cpp_def.replace(";", "")
        # TODO 
        cpp_def = cpp_def.replace("static", "")
        cpp_def = cpp_def.replace("MSSpectrum<>", "MSSpectrum[Peak1D]")
        cpp_def = cpp_def.replace("MSChromatogram<>", "MSChromatogram[ChromatogramPeak]")
        cpp_def = cpp_def.replace("std::vector", "libcpp_vector")
        cpp_def = cpp_def.replace("std::map", "libcpp_map")
        cpp_def = cpp_def.replace("std::pair", "libcpp_pair")
        cpp_def = cpp_def.replace("std::set", "libcpp_set")
        cpp_def = cpp_def.replace("std::string", "libcpp_string")
        # TODO operator< ...
        cpp_def = cpp_def.replace("<", "[")    
        cpp_def = cpp_def.replace(">", "]")    
        cpp_def = cpp_def.replace("const ", "")    
        cpp_def = cpp_def.replace("libcpp_vector[ DoubleReal ]", "libcpp_vector[ double ]")    
        cpp_def = cpp_def.replace("RichPeakSpectrum", "MSSpectrum[RichPeak1D]")
        cpp_def = cpp_def.replace("RichPeakMap", "MSExperiment[RichPeak1D, ChromatogramPeak]")
        # cpp_def = cpp_def.replace("Chromatogram", "MSChromatogram[ChromatogramPeak]")
        #
        # TODO replace python keywords: except, type, lamdba, map ...
        cpp_def = cpp_def.replace("PeakSpectrum", "MSSpectrum[Peak1D]")
        cpp_def = cpp_def.replace("PeakMap", "MSExperiment[Peak1D, ChromatogramPeak]")

        # comment out things that have we cannot wrap (raw pointers, iterators)
        if cpp_def.find("*") != -1 or
           cpp_def.find("::iterator") != -1:
            cpp_def = "# " + cpp_def

        return cpp_def.strip()


class IgnoreFile(object):

    def __init__(self):
        self.data = {
            "IgnoreNames" : [],
            "IgnoreMethods" : {},
        }

    def load(self, fname):
        self.fname = fname
        self.data = yaml.load(open(self.fname) )["PyOpenMSChecker"]

    def isNameIgnored(self, name):
        return name in self.data["IgnoreNames"]

    def getIgnoredMethods(self, name):
        return self.data["IgnoreMethods"].get(name, [])
        

class PXDFile(object):

    def __init__(self):
        pass

    def parse(self, pxdfile, comp_name):
        cython_file = parse_pxd_file(pxdfile)
        found = False

        def cimport(b, _, __):
            print "cimport", b.module_name, "as", b.as_name

        handlers = { CEnumDefNode : EnumDecl.parseTree,
                     CppClassNode : CppClassDecl.parseTree,
                     CTypeDefNode : CTypeDefDecl.parseTree,
                     CVarDefNode  : MethodOrAttributeDecl.parseTree,
                     CImportStatNode  : cimport,
                     }

        for klass in cython_file:
            if klass[0].cname == comp_name:
                found = True
                break
        if not found: 
            error_str = "Could not find a match for class %s in file %s" % (comp_name, pxdfile)
            raise Exception(error_str)

        # Check if we really have a class, then initialize it
        if isinstance(klass[0], CppClassNode):
            cl = CppClassDecl.parseTree(klass[0], klass[1], klass[2])
        else: 
            print "Something is wrong, not a class"
            raise Exception("wrong")

        for klass in cython_file:
            handler = handlers.get(type(klass[0]))
            res = handler(klass[0], klass[1], klass[2])
            if res.annotations.has_key("wrap-attach"):
                if res.annotations["wrap-attach"] == cl.name:
                    ## attach this to the above class
                    cl.methods[res.name] = res

        return cl

def main(options):

    bin_path = options.bin_path

    xml_output_path = os.path.join(bin_path, "doc/xml_output/")
    xml_files = glob.glob(xml_output_path + "/*.xml")
    # also look at /doc/doxygen/doxygen-error.log ?
    pxd_file_matching = create_pxd_file_map(bin_path)
    cnt = Counter()
    cnt.total = len(xml_files)
    ignorefile = IgnoreFile()
    if len(options.ignorefile) > 0:
        ignorefile.load(options.ignorefile)

    for f in xml_files:
        dfile = DoxygenXMLFile(f)
        res = dfile.parse()
        if dfile.parsing_error:
            # e.g. <computeroutput><bold></computeroutput>
            print "Skip:: No-parse :: could not parse file", f
            cnt.skipped_could_not_parse += 1
            continue
        if os.path.basename(f) == "index.xml":
            # Skip the index
            continue
        compound = res.get_compounddef()
        comp_name = compound.get_compoundname()

        if ignorefile.isNameIgnored(comp_name):
            print "Skip:: Ignored :: Class %s (file %s)", (comp_name, f)
            continue
        if compound.prot != "public":
            print "Skip:: Protected :: Compound %s is not public, skip" % (comp_name)
            cnt.skipped_protected += 1
            continue
        file_location = dfile.getCompoundFileLocation()
        if file_location is None:
            print "Skip:: No-data :: there is no source file for ", f
            cnt.skipped_no_location += 1
            continue
        openms_file = OpenMSSourceFile(file_location)
        maintainer = openms_file.getMaintainer()
        if dfile.empty(True):
            print "Skip:: No-data :: File is empty (no section definitions found or only definitions found) in file", f
            cnt.skipped_no_sections += 1
            continue
        if file_location in pxd_file_matching:
            pxdfile = pxd_file_matching[file_location]
        else:
            print "Skip:: No-pxd :: No pxd file exists for Class %s (File %s) %s" % (comp_name, file_location, f)
            cnt.skipped_no_pxd_file += 1
            pxd_text = dfile.get_pxd_from_class(compound, file_location, xml_output_path)
            if options.print_pxd: 
                print ""
                print pxd_text
            if len(options.pxds_out) > 0 and pxd_text is not None:
                fname =  os.path.join(options.pxds_out, "%s.pxd" % comp_name.split("::")[-1] )
                with open(fname, "w" ) as f:
                    f.write(pxd_text)
            continue
        try:
            cl = PXDFile().parse(pxdfile, comp_name)
        except Exception as e:
            # TODO specific exception
            print "Skip:: No-pxd :: " , e.message
            cnt.skipped_no_pxd_match += 1
            continue
        print "== Start to parse element %s - from Cpp file %s with maintainer %s and corresponding pxd file %s" % (
            comp_name, file_location, maintainer, pxdfile)
        cnt.parsed += 1
        leave = False
        # Loop through all sections (these are doxygen sections, not
        # interesting for our purposes) and then through all members
        for sdef in compound.get_sectiondef():
            for mdef in sdef.get_memberdef():
                if mdef.get_name() in ignorefile.getIgnoredMethods(comp_name):
                    print "Ignore member function/attribute : ", mdef.kind,  mdef.prot, mdef.name
                    continue
                handle_member_definition(mdef, cnt, cl)
    cnt.print_stats()
    cnt.print_skipping_reason()

def handle_args():
    usage = "" 

    parser = argparse.ArgumentParser(description = usage )
    parser.add_argument("--bin_path", dest="bin_path", default=".", help="OpenMS build path")
    parser.add_argument("--src_path", dest="src_path", default=".", help="OpenMS source path")
    parser.add_argument("--ignore-file", dest="ignorefile", default="", help="Checker ignore file")
    parser.add_argument("--pxds-out", dest="pxds_out", default="", help="Folder to write pxd files")
    parser.add_argument('--print_pxd', action='store_true', default=False)
    #   print "Usage: checker.php <OpenMS src path> <OpenMS build path> [-u \"user name\"] [-t test] [options]\n";

    args = parser.parse_args(sys.argv[1:])
    return args

if __name__=="__main__":
    options = handle_args()
    main(options)

