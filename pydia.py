"""
Python script for the Debug Interface Access SDK.

History:
    v1 - simple script with linear operations; XXX similar operations all over the place
    v2 - recreated centered around symbol classes; XXX symbols of the same type differ based on how we got them
    v3 - recreated centered around printers (perpectives?)
"""
from comtypes.client import GetModule, CreateObject
import comtypes
import time
import string
import sys

"""
TODO vc6 produces unsigned char for bool symbols (check undecorated name when available)
TODO vc6 inverts the order of the constructors
TODO add global options that control how things as generated to pydia
"""

def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    return type('Enum', (), enums)


SYMTAG = enum("SymTagNull","SymTagExe","SymTagCompiland","SymTagCompilandDetails","SymTagCompilandEnv",
              "SymTagFunction","SymTagBlock","SymTagData","SymTagAnnotation","SymTagLabel",
              "SymTagPublicSymbol","SymTagUDT","SymTagEnum","SymTagFunctionType","SymTagPointerType",
              "SymTagArrayType","SymTagBaseType","SymTagTypedef","SymTagBaseClass","SymTagFriend",
              "SymTagFunctionArgType","SymTagFuncDebugStart","SymTagFuncDebugEnd","SymTagUsingNamespace","SymTagVTableShape",
              "SymTagVTable","SymTagCustom","SymTagThunk","SymTagCustomType","SymTagManagedType",
              "SymTagDimension","SymTagCallSite","SymTagMax")
def SYMTAG_name(value):
    for name in SYMTAG.__dict__.keys():
        if name.startswith("SymTag") and getattr(SYMTAG, name) == value:
            return name
    return "SYMTAG_name({})".format(value)

BASICTYPE = enum(
    btNoType   = 0,
    btVoid     = 1,
    btChar     = 2,
    btWChar    = 3,
    btInt      = 6,
    btUInt     = 7,
    btFloat    = 8,
    btBCD      = 9,
    btBool     = 10,
    btLong     = 13,
    btULong    = 14,
    btCurrency = 25,
    btDate     = 26,
    btVariant  = 27,
    btComplex  = 28,
    btBit      = 29,
    btBSTR     = 30,
    btHresult  = 31)
def BASICTYPE_name(value):
    for name in BASICTYPE.__dict__.keys():
        if name.startswith("bt") and getattr(BASICTYPE, name) == value:
            return name
    return "BASICTYPE_name({})".format(value)
def BASICTYPE_str(value, length):
    k = (value, length)
    if k == (BASICTYPE.btNoType,0): return "..." # vararg argument type
    if k == (BASICTYPE.btVoid,0): return "void" # void type
    if k == (BASICTYPE.btChar,1): return "char" # char WITHOUT signed/unsigned type
    if k == (BASICTYPE.btWChar,2): return "wchar_t" # wide character type
    if k == (BASICTYPE.btInt,1): return "signed char" # signed integer type EXCEPT long
    if k == (BASICTYPE.btInt,2): return "short"
    if k == (BASICTYPE.btInt,4): return "int"
    if k == (BASICTYPE.btInt,8): return "__int64" # (long long)
    if k == (BASICTYPE.btUInt,1): return "unsigned char" # unsigned integer type EXCEPT long
    if k == (BASICTYPE.btUInt,2): return "unsigned short"
    if k == (BASICTYPE.btUInt,4): return "unsigned int"
    if k == (BASICTYPE.btUInt,8): return "unsigned __int64" # (unsigned long long)
    if k == (BASICTYPE.btFloat,4): return "float" # floating-point number type
    if k == (BASICTYPE.btFloat,8): return "double"
    if k == (BASICTYPE.btBool,1): return "bool" # boolean type
    if k == (BASICTYPE.btLong,4): return "long" # signed long int type
    if k == (BASICTYPE.btULong,4): return "unsigned long" # unsigned long int type
    return "BASICTYPE_str({}, {})".format(value, length)

LOCATIONTYPE = enum("LocIsNull","LocIsStatic","LocIsTLS","LocIsRegRel","LocIsThisRel",
                    "LocIsEnregistered","LocIsBitField","LocIsSlot","LocIsIlRel","LocInMetaData",
                    "LocIsConstant","LocTypeMax")
def LOCATIONTYPE_name(value):
    for name in LOCATIONTYPE.__dict__.keys():
        if name.startswith("Loc") and getattr(LOCATIONTYPE, name) == value:
            return name
    return "LOCATIONTYPE_name({})".format(value)

DATAKIND = enum("DataIsUnknown","DataIsLocal","DataIsStaticLocal","DataIsParam","DataIsObjectPtr",
                "DataIsFileStatic","DataIsGlobal","DataIsMember","DataIsStaticMember","DataIsConstant")
def DATAKIND_name(value):
    for name in DATAKIND.__dict__.keys():
        if name.startswith("Data") and getattr(DATAKIND, name) == value:
            return name
    return "DATAKIND_name({})".format(value)

UDTKIND = enum("UdtStruct","UdtClass","UdtUnion")
def UDTKIND_name(value):
    for name in UDTKIND.__dict__.keys():
        if name.startswith("Udt") and getattr(UDTKIND, name) == value:
            return name
    return "UDTKIND_name({})".format(value)
def UDTKIND_str(value):
    if value == UDTKIND.UdtStruct: return "struct"
    if value == UDTKIND.UdtClass: return "class"
    if value == UDTKIND.UdtUnion: return "union"
    return "UDTKIND_str({})".format(value)

CVACCESS = enum(
    CV_private   = 1,
    CV_protected = 2,
    CV_public    = 3)
def CVACCESS_name(value):
    for name in CVACCESS.__dict__.keys():
        if name.startswith("CV_") and getattr(CVACCESS, name) == value:
            return name
    return "CVACCESS_name({})".format(value)
def CVACCESS_str(value):
    if value == CVACCESS.CV_private: return "private"
    if value == CVACCESS.CV_protected: return "protected"
    if value == CVACCESS.CV_public: return "public"
    return "CVACCESS_str({})".format(value)

CVCALL = enum(
    CV_CALL_NEAR_C      = 0x00, # near right to left push, caller pops stack
    CV_CALL_FAR_C       = 0x01, # far right to left push, caller pops stack
    CV_CALL_NEAR_PASCAL = 0x02, # near left to right push, callee pops stack
    CV_CALL_FAR_PASCAL  = 0x03, # far left to right push, callee pops stack
    CV_CALL_NEAR_FAST   = 0x04, # near left to right push with regs, callee pops stack
    CV_CALL_FAR_FAST    = 0x05, # far left to right push with regs, callee pops stack
    CV_CALL_SKIPPED     = 0x06, # skipped (unused) call index
    CV_CALL_NEAR_STD    = 0x07, # near standard call
    CV_CALL_FAR_STD     = 0x08, # far standard call
    CV_CALL_NEAR_SYS    = 0x09, # near sys call
    CV_CALL_FAR_SYS     = 0x0a, # far sys call
    CV_CALL_THISCALL    = 0x0b, # this call (this passed in register)
    CV_CALL_MIPSCALL    = 0x0c, # Mips call
    CV_CALL_GENERIC     = 0x0d, # Generic call sequence
    CV_CALL_ALPHACALL   = 0x0e, # Alpha call
    CV_CALL_PPCCALL     = 0x0f, # PPC call
    CV_CALL_SHCALL      = 0x10, # Hitachi SuperH call
    CV_CALL_ARMCALL     = 0x11, # ARM call
    CV_CALL_AM33CALL    = 0x12, # AM33 call
    CV_CALL_TRICALL     = 0x13, # TriCore Call
    CV_CALL_SH5CALL     = 0x14, # Hitachi SuperH-5 call
    CV_CALL_M32RCALL    = 0x15, # M32R Call
    CV_CALL_CLRCALL     = 0x16, # clr call
    CV_CALL_RESERVED    = 0x17) # first unused call enumeration
def CVCALL_name(value):
    for name in CVCALL.__dict__.keys():
        if name.startswith("CV_CALL_") and getattr(CVCALL, name) == value:
            return name
    return "CVCALL_name({})".format(value)
def CVCALL_str(value):
    if value == CVCALL.CV_CALL_NEAR_STD: return "__stdcall"
    if value == CVCALL.CV_CALL_THISCALL: return "__thiscall"
    return "CVCALL_str({})".format(value)

def hexValue(value,length):
    assert length > 0
    bits = length * 8
    mask = (1 << bits) - 1
    return "0x{:X}".format(value & mask)


def DEBUG(context,*args):
    print ' '.join(["[%s]" % str(context)] + [str(arg) for arg in args]) + '\r\n',


class DiaEnumSymbolsIterator:
    """Iterates over the symbols in a IDiaEnumSymbols."""

    def __init__(self, symbols):
        self.symbols = symbols

    def __getitem__(self, item):
        assert isinstance(item, int)
        if item >= 0 and item < len(self):
            return self.symbols.Item(item)
        raise IndexError

    def __len__(self):
        if self.symbols:
            return self.symbols.count
        return 0


class SymbolPrinter:
    """I provide attributes, metadata and print the attributes of a symbol with DEBUG."""
    pydia = None
    options = None

    def __init__(self, pydia, **kwargs):
        assert pydia
        if isinstance(pydia, SymbolPrinter):
            self.pydia = pydia.pydia
        else:
            self.pydia = pydia
        self.options = dict(kwargs)

    def defaultOption(self, name):
        """Return the default value of a particular option"""
        return None

    def option(self, name):
        """Return the value of a particular option"""
        return self.options.setdefault(name, self.defaultOption(name))

    def attributes(self, symbol=None, symTag=None):
        """Return a tupple with all the symTag or symbol.symTag attributes"""
        if symTag is None:
            assert symbol
            symTag = symbol.symTag
        if symTag == SYMTAG.SymTagNull:
            return ("access","addressOffset","addressSection","addressTaken","age",
                    "arrayIndexType","arrayIndexTypeId","backEndBuild","backEndMajor","backEndMinor",
                    "backEndQFE","baseType","bitPosition","callingConvention","classParent",
                    "classParentId","code","compilerGenerated","compilerName","constType",
                    "constructor","container","count","countLiveRanges","customCallingConvention",
                    "dataKind","editAndContinueEnabled","farReturn","framePointerPresent","frontEndBuild",
                    "frontEndMajor","frontEndMinor","frontEndQFE","function","guid",
                    "hasAlloca","hasAssignmentOperator","hasCastOperator","hasDebugInfo","hasEH",
                    "hasEHa","hasInlAsm","hasLongJump","hasManagedCode","hasNestedTypes",
                    "hasSEH","hasSecurityChecks","hasSetJump","hfaDouble","hfaFloat",
                    "indirectVirtualBaseClass","inlSpec","interruptReturn","intrinsic","intro",
                    "isAggregated","isCTypes","isCVTCIL","isConstructorVirtualBase","isCxxReturnUdt",
                    "isDataAligned","isHotpatchable","isLTCG","isMSILNetmodule","isNaked",
                    "isSafeBuffers","isSplitted","isStatic","isStripped","language",
                    "length","lexicalParent","lexicalParentId","libraryName","liveRangeLength",
                    "liveRangeStartAddressOffset","liveRangeStartAddressSection","liveRangeStartRelativeVirtualAddress","localBasePointerRegisterId","locationType",
                    "lowerBound","lowerBoundId","machineType","managed","msil",
                    "name","nested","noInline","noReturn","noStackOrdering",
                    "notReached","objectPointerType","oemId","oemSymbolId","offset",
                    "offsetInUdt","optimizedCodeDebugInfo","overloadedOperator","packed","paramBasePointerRegisterId",
                    "platform","pure","rank","reference","registerId",
                    "relativeVirtualAddress","scoped","sealed","signature","slot",
                    "sourceFileName","strictGSCheck","symIndexId","symTag","symbolsFileName",
                    "targetOffset","targetRelativeVirtualAddress","targetSection","targetVirtualAddress","thisAdjust",
                    "thunkOrdinal","timeStamp","token","type","typeId",
                    "udtKind","unalignedType","undecoratedName","unmodifiedType","unused",
                    "upperBound","upperBoundId","value","virtual","virtualAddress",
                    "virtualBaseClass","virtualBaseDispIndex","virtualBaseOffset","virtualBasePointerOffset","virtualBaseTableType",
                    "virtualTableShape","virtualTableShapeId","volatileType","wasInlined")
        if symTag == SYMTAG.SymTagFunction:
            return ("access","addressOffset","addressSection","classParent","classParentId",
                    "constType","customCallingConvention","farReturn","hasAlloca","hasEH",
                    "hasEHa","hasInlAsm","hasLongJump","hasSecurityChecks","hasSEH",
                    "hasSetJump","interruptReturn","intro","InlSpec","isNaked",
                    "isStatic","length","lexicalParent","lexicalParentId","locationType",
                    "name","noInline","notReached","noReturn","noStackOrdering",
                    "optimizedCodeDebugInfo","pure","relativeVirtualAddress","symIndexId","symTag",
                    "token","type","typeId","unalignedType","undecoratedName",
                    "virtual","virtualAddress","virtualBaseOffset","volatileType")
        if symTag == SYMTAG.SymTagFunctionType:
            return ("callingConvention","classParent","classParentId","constType","count",
                    "lexicalParent","lexicalParentId","objectPointerType","symIndexId","symTag",
                    "thisAdjust","type","typeId","unalignedType","volatileType")
        if symTag == SYMTAG.SymTagFuncDebugStart:
            return ("addressOffset","addressSection","customCallingConvention","farReturn","farReturn",
                    "isStatic","lexicalParent","lexicalParentId","locationType","noInline",
                    "noReturn","notReached","offset","optimizedCodeDebugInfo","relativeVirtualAddress",
                    "symIndexId","symTag","virtualAddress")
        if symTag == SYMTAG.SymTagFuncDebugEnd:
            return ("addressOffset","addressSection","customCallingConvention","farReturn","interruptReturn",
                    "isStatic","lexicalParent","lexicalParentId","locationType","noInline",
                    "noReturn","notReached","offset","optimizedCodeDebugInfo","symIndexId",
                    "relativeVirtualAddress","symTag","virtualAddress")
        if symTag == SYMTAG.SymTagData:
            return ("access","addressOffset","addressSection","addressTaken","bitPosition",
                    "classParent","classParentId","compilerGenerated","constType","dataKind",
                    "isAggregated","isSplitted","length","lexicalParent","lexicalParentId",
                    "locationType","name","offset","registerId","relativeVirtualAddress",
                    "slot","symIndexId","symTag","token","type",
                    "typeId","unalignedType","value","virtualAddress","volatileType")
        if symTag == SYMTAG.SymTagBaseType:
            return ("baseType","constType","length","lexicalParent","lexicalParentId",
                    "symIndexId","symTag","unalignedType","volatileType")
        if symTag == SYMTAG.SymTagFunctionArgType:
            return ("classParent","classParentId","lexicalParent","lexicalParentId","symIndexId",
                    "symTag","type","typeId")
        if symTag == SYMTAG.SymTagUDT:
            return ("classParent","classParentId","constructor","constType","hasAssignmentOperator",
                    "hasCastOperator","hasNestedTypes","length","lexicalParent","lexicalParentId",
                    "name","nested","overloadedOperator","packed","scoped",
                    "symIndexId","symTag","udtKind","unalignedType","virtualTableShape",
                    "virtualTableShapeId","volatileType")
        if symTag == SYMTAG.SymTagVTable:
            return ("classParent","classParentId","constType","lexicalParent","lexicalParentId",
                    "symIndexId","symTag","type","typeId","unalignedType",
                    "volatileType")
        if symTag == SYMTAG.SymTagPointerType:
            return ("constType","length","lexicalParent","lexicalParentId","reference",
                    "symIndexId","symTag","type","typeId","unalignedType",
                    "volatileType")
        if symTag == SYMTAG.SymTagVTableShape:
            return ("constType","count","lexicalParent","lexicalParentId","symIndexId",
                    "symTag","unalignedType","volatileType")
        if symTag == SYMTAG.SymTagTypedef:
            return ("baseType","classParent","classParentId","constructor","constType",
                    "hasAssignmentOperator","hasCastOperator","hasNestedTypes","length","lexicalParent",
                    "lexicalParentId","name","nested","overloadedOperator","packed",
                    "reference","scoped","symIndexId","symTag","type",
                    "typeId","udtKind","unalignedType","virtualTableShape","virtualTableShapeId",
                    "volatileType")
        if symTag == SYMTAG.SymTagBaseClass:
            return ("access","classParent","classParentId","constructor","constType",
                    "hasAssignmentOperator","hasCastOperator","hasNestedTypes","indirectVirtualBaseClass","length",
                    "lexicalParent","lexicalParentId","name","nested","offset",
                    "overloadedOperator","packed","scoped","symIndexId","symTag",
                    "type","typeId","udtKind","unalignedType","virtualBaseClass",
                    "virtualBaseDispIndex","virtualBasePointerOffset","virtualBaseTableType","virtualTableShape","virtualTableShapeId",
                    "volatileType")
        if symTag == SYMTAG.SymTagArrayType:
            return ("arrayIndexType","arrayIndexTypeId","constType","count","length",
                    "lexicalParent","lexicalParentId","rank","symIndexId","symTag",
                    "type","typeId","unalignedType","volatileType")
        if symTag == SYMTAG.SymTagEnum:
            return ("baseType","classParent","classParentId","constructor","constType",
                    "hasAssignmentOperator","hasCastOperator","hasNestedTypes","length","lexicalParent",
                    "lexicalParentId","name","nested","overloadedOperator","packed",
                    "scoped","symIndexId","symTag","type","typeId",
                    "unalignedType","volatileType")
        if symTag == SYMTAG.SymTagCompiland:
            return ("backEndBuild","backEndMajor","backEndMinor","compilerName","editAndContinueEnabled",
                    "frontEndBuild","frontEndMajor","frontEndMinor","hasDebugInfo","hasManagedCode",
                    "hasSecurityChecks","isCVTCIL","isDataAligned","isHotpatchable","isLTCG",
                    "isMSILNetmodule","language","lexicalParent","lexicalParentId","platform",
                    "symIndexId","symTag")
        if symTag == SYMTAG.SymTagExe:
            return ("age","guid","isCTypes","isStripped","machineType",
                    "name","signature","symbolsFileName","symIndexId",
                    "symTag")
        if symTag == SYMTAG.SymTagCallSite:
            return self.attributes(symTag=SYMTAG.SymTagNull) # TODO no information
        assert False, "TODO symTag={}".format(SYMTAG_name(symTag))

    def debugSymbol(self, symbol, symTag=None):
        """Debug all the symbol attributes of symTag or symbol.symTag"""
        assert symbol
        if symTag is None: symTag = symbol.symTag
        context = SYMTAG_name(symTag)
        DEBUG(context, symbol)
        for attr in self.attributes(symTag=symTag):
            try:
                result = getattr(symbol, attr)
            except comtypes.COMError, e:
                result = e
            DEBUG(context, attr, result)

    def name(self, symbol):
        self.validate(symbol)
        name = symbol.name.split("::")
        return name[-1]

    def metadata(self, symbol):
        """Return a list of metadata tokens"""
        self.validate(symbol)
        m = []
        ##DONE = ("access","addressOffset","addressSection","addressTaken","age",)
        if symbol.access: m.append("<access={}>".format(CVACCESS_str(symbol.access)))
        if symbol.addressOffset: m.append("<addressOffset={}>".format(symbol.addressOffset))
        if symbol.addressSection: m.append("<addressSection={}>".format(symbol.addressSection))
        if symbol.addressTaken: m.append("<addressTaken>")
        if symbol.age: m.append("<age={}>".format(symbol.age))
        #TODO = ("arrayIndexType","arrayIndexTypeId","backEndBuild","backEndMajor","backEndMinor",)
        if symbol.backEndBuild: m.append("<backEndBuild={}>".format(symbol.backEndBuild))
        if symbol.backEndMajor: m.append("<backEndMajor={}>".format(symbol.backEndMajor))
        if symbol.backEndMinor: m.append("<backEndMinor={}>".format(symbol.backEndMinor))
        #TODO = ("backEndQFE","baseType","bitPosition","callingConvention","classParent",)
        if symbol.baseType: m.append("<baseType={}>".format(BASICTYPE_name(symbol.baseType)))
        if symbol.bitPosition: m.append("<bitPosition={}>".format(symbol.bitPosition))
        if symbol.callingConvention: m.append("<callingConvention={}>".format(CVCALL_name(symbol.callingConvention)))
        #TODO = ("classParentId","code","compilerGenerated","compilerName","constType")
        if symbol.compilerGenerated: m.append("<compilerGenerated>")
        if symbol.compilerName: m.append("<compilerName={}>".format(symbol.compilerName))
        if symbol.constType: m.append("<constType>")
        #TODO = ("constructor","container","count","countLiveRanges","customCallingConvention",)
        if symbol.constructor: m.append("<constructor>")
        if symbol.count: m.append("<count={}>".format(symbol.count))
        if symbol.customCallingConvention: m.append("<customCallingConvention>")
        #TODO = ("dataKind","editAndContinueEnabled","farReturn","framePointerPresent","frontEndBuild",)
        if symbol.dataKind: m.append("<dataKind={}>".format(DATAKIND_name(symbol.dataKind)))
        if symbol.editAndContinueEnabled: m.append("<editAndContinueEnabled>")
        if symbol.farReturn: m.append("<farReturn>")
        if symbol.frontEndBuild: m.append("<frontEndBuild={}>".format(symbol.frontEndBuild))
        #TODO = ("frontEndMajor","frontEndMinor","frontEndQFE","function","guid",)
        if symbol.frontEndMajor: m.append("<frontEndMajor={}>".format(symbol.frontEndMajor))
        if symbol.frontEndMinor: m.append("<frontEndMinor={}>".format(symbol.frontEndMinor))
        if symbol.guid: m.append("<guid={}>".format(symbol.guid))
        ##DONE = ("hasAlloca","hasAssignmentOperator","hasCastOperator","hasDebugInfo","hasEH",)
        if symbol.hasAlloca: m.append("<hasAlloca>")
        if symbol.hasAssignmentOperator: m.append("<hasAssignmentOperator>")
        if symbol.hasCastOperator: m.append("<hasCastOperator>")
        if symbol.hasDebugInfo: m.append("<hasDebugInfo>")
        if symbol.hasEH: m.append("<hasEH>")
        #TODO = ("hasEHa","hasInlAsm","hasLongJump","hasManagedCode","hasNestedTypes",)
        if symbol.hasEHa: m.append("<hasEHa>")
        if symbol.hasInlAsm: m.append("<hasInlAsm>")
        if symbol.hasManagedCode: m.append("<hasManagedCode>")
        if symbol.hasNestedTypes: m.append("<hasNestedTypes>")
        #TODO = ("hasSEH","hasSecurityChecks","hasSetJump","hfaDouble","hfaFloat",)
        if symbol.hasSEH: m.append("<hasSEH>")
        if symbol.hasSecurityChecks: m.append("<hasSecurityChecks>")
        if symbol.hasSetJump: m.append("<hasSetJump>")
        #TODO = ("indirectVirtualBaseClass","inlSpec","interruptReturn","intrinsic","intro",)
        if symbol.indirectVirtualBaseClass: m.append("<indirectVirtualBaseClass>")
        if symbol.inlSpec: m.append("<inlSpec>")
        if symbol.interruptReturn: m.append("<interruptReturn>")
        if symbol.intro: m.append("<intro>")
        #TODO = ("isAggregated","isCTypes","isCVTCIL","isConstructorVirtualBase","isCxxReturnUdt",)
        if symbol.isAggregated: m.append("<isAggregated>")
        if symbol.isCTypes: m.append("<isCTypes>")
        if symbol.isCVTCIL: m.append("<isCVTCIL>")
        ##DONE = ("isDataAligned","isHotpatchable","isLTCG","isMSILNetmodule","isNaked",)
        if symbol.isDataAligned: m.append("<isDataAligned>")
        if symbol.isHotpatchable: m.append("<isHotpatchable>")
        if symbol.isLTCG: m.append("<isLTCG>")
        if symbol.isMSILNetmodule: m.append("<isMSILNetmodule>")
        if symbol.isNaked: m.append("<isNaked>")
        #TODO = ("isSafeBuffers","isSplitted","isStatic","isStripped","language",)
        if symbol.isSplitted: m.append("<isSplitted>")
        if symbol.isStatic: m.append("<isStatic>")
        if symbol.isStripped: m.append("<isStripped>")
        if symbol.language: m.append("<language={}>".format(symbol.language))
        #TODO = ("length","lexicalParent","lexicalParentId","libraryName","liveRangeLength",)
        if symbol.length: m.append("<length={}>".format(symbol.length))
        #TODO = ("liveRangeStartAddressOffset","liveRangeStartAddressSection","liveRangeStartRelativeVirtualAddress","localBasePointerRegisterId","locationType",)
        if symbol.locationType: m.append("<locationType={}>".format(LOCATIONTYPE_name(symbol.locationType)))
        #TODO = ("lowerBound","lowerBoundId","machineType","managed","msil",)
        if symbol.machineType: m.append("<machineType={}>".format(symbol.machineType))
        ##DONE = ("name","nested","noInline","noReturn","noStackOrdering",)
        if symbol.name: m.append("<name={}>".format(symbol.name))
        if symbol.nested: m.append("<nested>")
        if symbol.noInline: m.append("<noInline>")
        if symbol.noReturn: m.append("<noReturn>")
        if symbol.noStackOrdering: m.append("<noStackOrdering>")
        #TODO = ("notReached","objectPointerType","oemId","oemSymbolId","offset",)
        if symbol.notReached: m.append("<notReached>")
        if symbol.offset: m.append("<offset={}>".format(symbol.offset))
        #TODO = ("offsetInUdt","optimizedCodeDebugInfo","overloadedOperator","packed","paramBasePointerRegisterId",)
        if symbol.optimizedCodeDebugInfo: m.append("<optimizedCodeDebugInfo>")
        if symbol.overloadedOperator: m.append("<overloadedOperator>")
        if symbol.packed: m.append("<packed>")
        #TODO = ("platform","pure","rank","reference","registerId",)
        if symbol.platform: m.append("<platform={}>".format(symbol.platform))
        if symbol.pure: m.append("<pure>")
        if symbol.registerId: m.append("<registerId={}>".format(symbol.registerId))
        #TODO = ("relativeVirtualAddress","scoped","sealed","signature","slot",)
        if symbol.relativeVirtualAddress: m.append("<relativeVirtualAddress={}>".format(symbol.relativeVirtualAddress))
        if symbol.scoped: m.append("<scoped>")
        if symbol.signature: m.append("<signature={}>".format(symbol.signature))
        if symbol.slot: m.append("<slot={}>".format(symbol.slot))
        #TODO = ("sourceFileName","strictGSCheck","symIndexId","symTag","symbolsFileName",)
        if symbol.symTag: m.append("<symTag={}>".format(SYMTAG_name(symbol.symTag)))
        if symbol.symbolsFileName: m.append("<symbolsFileName={}>".format(symbol.symbolsFileName))
        #TODO = ("targetOffset","targetRelativeVirtualAddress","targetSection","targetVirtualAddress","thisAdjust",)
        if symbol.thisAdjust: m.append("<thisAdjust={}>".format(symbol.thisAdjust))
        #TODO = ("thunkOrdinal","timeStamp","token","type","typeId",)
        if symbol.token: m.append("<token={}>".format(symbol.token))
        #TODO = ("udtKind","unalignedType","undecoratedName","unmodifiedType","unused",)
        if symbol.unalignedType: m.append("<unalignedType>")
        if symbol.undecoratedName: m.append("<undecoratedName={}>".format(symbol.undecoratedName))
        #TODO = ("upperBound","upperBoundId","value","virtual","virtualAddress",)
        if symbol.value: m.append("<value={}>".format(symbol.value))
        if symbol.virtual: m.append("<virtual>")
        if symbol.virtualAddress: m.append("<virtualAddress={}>".format(symbol.virtualAddress))
        #TODO = ("virtualBaseClass","virtualBaseDispIndex","virtualBaseOffset","virtualBasePointerOffset","virtualBaseTableType",)
        if symbol.virtualBaseClass: m.append("<virtualBaseClass>")
        if symbol.virtualBaseDispIndex: m.append("<virtualBaseDispIndex={}>".format(symbol.virtualBaseDispIndex))
        if symbol.virtualBasePointerOffset: m.append("<virtualBasePointerOffset={}>".format(symbol.virtualBasePointerOffset))
        if symbol.virtualBaseOffset: m.append("<virtualBaseOffset={}>".format(symbol.virtualBaseOffset))
        #TODO = ("virtualTableShape","virtualTableShapeId","volatileType","wasInlined")
        if symbol.volatileType: m.append("<volatileType>")
        return m

    def validate(self, symbol):
        """Assert the symbol is valid"""
        pass


class TypePrinter(SymbolPrinter):
    """I can declare types."""

    def defaultOption(self, name):
        if name == "name": return None
        if name == "className": return None
        if name == "paramNames": return []
        if name == "showReturn": return True
        if name == "showThiscall": return True
        assert False, "unexpected option '{}'".format(name)

    def validate(self, symbol):
        assert symbol.symTag in (SYMTAG.SymTagBaseType, SYMTAG.SymTagPointerType, SYMTAG.SymTagFunctionType, SYMTAG.SymTagEnum, SYMTAG.SymTagUDT, SYMTAG.SymTagArrayType)
        assert symbol.lexicalParent.symTag == SYMTAG.SymTagExe

    def params(self, symbol):
        self.validate(symbol)
        assert symbol.symTag == SYMTAG.SymTagFunctionType
        params = []
        for child in DiaEnumSymbolsIterator(symbol.findChildrenEx(SYMTAG.SymTagNull, None, 0)):
            childSymTag = child.symTag
            if childSymTag == SYMTAG.SymTagFunctionArgType:
                params.append(child)
            else:
                DEBUG("SymTagFunctionType.child")
                self.debugSymbol(child)
                assert False, "TODO"
        return params

    def declare(self, symbol):
        self.validate(symbol)
        name = self.option("name")
        paramNames = self.option("paramNames")
        s = []
        symTag = symbol.symTag
        if symTag == SYMTAG.SymTagBaseType:
            if symbol.constType: s.append("const")
            if symbol.unalignedType: s.append("__unaligned")
            if symbol.volatileType: s.append("volatile")
            s.append(BASICTYPE_str(symbol.baseType, symbol.length))
        elif symTag == SYMTAG.SymTagPointerType:
            assert symbol.unalignedType == 0
            assert symbol.volatileType == 0
            if symbol.reference: pointerType = "&"
            else: pointerType = "*"
            s.append(TypePrinter(self).declare(symbol.type) + pointerType)
            if symbol.constType: s.append("const") # constant pointers have const at the end of the type
        elif symTag == SYMTAG.SymTagFunctionType:
            assert False, "use declareFunctionType or declareFunctionPointer"
        elif symTag == SYMTAG.SymTagEnum:
            s.append(EnumPrinter(self).declare(symbol))
        elif symTag == SYMTAG.SymTagUDT:
            s.append(UdtPrinter(self).declare(symbol))
        elif symTag == SYMTAG.SymTagArrayType:
            arrayIndexType = symbol.arrayIndexType
            assert arrayIndexType.symTag == SYMTAG.SymTagBaseType
            assert arrayIndexType.baseType in (BASICTYPE.btULong, BASICTYPE.btInt) # integer index
            assert symbol.constType == 0
            assert symbol.lexicalParent.symTag == SYMTAG.SymTagExe # must be global scope
            assert symbol.rank == 0
            assert symbol.unalignedType == 0
            assert symbol.volatileType == 0
            s.append(TypePrinter(self).declare(symbol.type))
            if name: s += [" ", name]
            s += ["[", str(symbol.count), "]"]
            return "".join(s)
        else:
            DEBUG("TypePrinter.declare", "TODO")
            self.debugSymbol(symbol)
            s.append("<TODO TypePrinter.declare.symTag={}>".format(SYMTAG_name(symTag)))
            s += self.metadata(symbol)
        if name: s.append(name)
        return " ".join(s)

    def declareFunctionType(self, symbol):
        self.validate(symbol)
        assert symbol.symTag == SYMTAG.SymTagFunctionType
        name = self.option("name")
        paramNames = self.option("paramNames")
        showReturn = self.option("showReturn")
        showThiscall = self.option("showThiscall")
        isConstFunction = symbol.objectPointerType and symbol.objectPointerType.type.constType
        s = []
        if showReturn:
            s.append(TypePrinter(self).declare(symbol.type))
        if showThiscall or symbol.callingConvention != CVCALL.CV_CALL_THISCALL:
            s.append(CVCALL_str(symbol.callingConvention))
        params = self.params(symbol)
        if len(paramNames) != len(params):
            if len(paramNames) != 0: assert False, "len({}) != {})".format(paramNames, len(params))
            paramNames = [None] * len(params) # names are not available
        params = [TypePrinter(self, name=paramNames[i]).declare(params[i].type) for i in xrange(len(params))]
        if len(params) == 0: params.append("void") # no paramenters
        if not name: assert False, "<TODO no name in TypePrinter.declareFunctionType>"
        s.append(name + "(" + ", ".join(params) + ")")
        if isConstFunction:
            s.append("const")
        return " ".join(s)

    def declareFunctionPointer(self, symbol):
        self.validate(symbol)
        #DEBUG("TypePrinter.declarePointer")
        #self.debugSymbol(symbol)
        assert symbol.symTag == SYMTAG.SymTagFunctionType
        name = self.option("name")
        className = self.option("className")
        paramNames = self.option("paramNames")
        showReturn = self.option("showReturn")
        showThiscall = self.option("showThiscall")
        isConstFunction = symbol.objectPointerType and symbol.objectPointerType.type.constType
        s = []
        if showReturn:
            s.append(self.declare(symbol.type))
        s.append(" (")
        if showThiscall or symbol.callingConvention != CVCALL.CV_CALL_THISCALL:
            s += [CVCALL_str(symbol.callingConvention), " "]
        if className:
            s += [className, "::"]
        s.append("*")
        if name: s += [" ", name]
        s.append(")(")
        params = self.params(symbol)
        if len(paramNames) != len(params):
            if len(paramNames) > 0:
                assert False, "len({}) != {})".format(paramNames, len(params))
            paramNames = [None] * len(params) # names are not available
        params = [TypePrinter(self, name=paramNames[i]).declare(params[i].type) for i in xrange(len(params))]
        if len(params) == 0: params.append("void") # no paramenters
        s.append(", ".join(params))
        s.append(")")
        if isConstFunction:
            s.append(" const")
        return "".join(s)


class FunctionPrinter(SymbolPrinter):
    """I can declare functions."""

    def defaultOption(self, name):
        if name == "className": return None
        assert False, "unexpected option '{}'".format(name)

    def validate(self, symbol):
        assert symbol.symTag == SYMTAG.SymTagFunction
        assert symbol.lexicalParent.symTag in (SYMTAG.SymTagCompiland, SYMTAG.SymTagExe)

    def paramNames(self, symbol):
        self.validate(symbol)
        params = []
        for child in DiaEnumSymbolsIterator(symbol.findChildrenEx(SYMTAG.SymTagData, None, 0)):
            if child.dataKind == DATAKIND.DataIsParam:
                params.append(child.name)
        undecoratedName = symbol.undecoratedName
        if undecoratedName and undecoratedName.find(" " + symbol.name + "(") == -1:
            DEBUG("FunctionPrinter.paramNames", "code was reused, ignoring params={} {}".format(params, " ".join(self.metadata(symbol))))
            name = self.name(symbol) # simple name of the function
            if undecoratedName.find("::" + name + "(") == -1 and undecoratedName.find(" " + name + "(") >= 0:
                #assert False, "not the same function"
                return []
        if undecoratedName and undecoratedName.find("...)") >= 0:
            # is a vararg function (this argument has no name)
            if len(params) > 0:
                # has a list of arguments
                params += [None]
            elif len(params) == 0 and undecoratedName.find("(...)") >= 0:
                # all ok, it's not missing arguments
                params += [None]
        return params

    def declareMemberLine(self, symbol):
        self.validate(symbol)
        assert symbol.locationType in (LOCATIONTYPE.LocIsStatic, LOCATIONTYPE.LocIsNull)
        # LocIsNull was seen with a function defined in the header and never used (optimized out?)
        s = []
        if symbol.compilerGenerated:
            s.append("// GENERATED //")
        s.append(CVACCESS_str(symbol.access) + ":")
        if symbol.isStatic: s.append("static")
        if symbol.virtual: s.append("virtual")
        if symbol.pure and symbol.virtual and symbol.intro: postfix = " = 0;"
        else: postfix = ";"
        className = self.option("className")
        name = self.name(symbol)
        paramNames = self.paramNames(symbol)
        showReturn = True
        showThiscall = False
        if symbol.constructor or (className and name == className):
            showReturn = False # constructor
        if name and name.startswith("~"):
            showReturn = False # destructor
        s.append(TypePrinter(self, name=name, paramNames=paramNames, showReturn=showReturn, showThiscall=showThiscall).declareFunctionType(symbol.type) + postfix)
        s.append("//")
        s += self.metadata(symbol)
        s.append("//")
        s += TypePrinter(self).metadata(symbol.type)
        return " ".join(s)

    def declareMemberPointer(self, symbol):
        self.validate(symbol)
        #DEBUG("FunctionPrinter.declareMemberPointer")
        #self.debugSymbol(symbol)
        assert symbol.classParent
        className = symbol.classParent.name
        paramNames = self.paramNames(symbol)
        return TypePrinter(self, className=className, paramNames=paramNames).declareFunctionPointer(symbol.type)


class DataPrinter(SymbolPrinter):
    """I can declare data."""

    def validate(self, symbol):
        assert symbol.symTag == SYMTAG.SymTagData
        assert symbol.lexicalParent.symTag == SYMTAG.SymTagExe

    def declareMemberLine(self, symbol):
        self.validate(symbol)
        s = []
        if symbol.dataKind == DATAKIND.DataIsMember and symbol.locationType == LOCATIONTYPE.LocIsThisRel:
            # normal member
            s.append("/* this+{} */".format(symbol.offset))#hexValue(symbol.offset, 4)))
            s.append(CVACCESS_str(symbol.access) + ":")
            s.append(TypePrinter(self, name=self.name(symbol)).declare(symbol.type) + ";")
            s.append("//")
            s += self.metadata(symbol)
            s.append("//")
            s += TypePrinter(self).metadata(symbol.type)
        elif symbol.dataKind == DATAKIND.DataIsStaticMember and symbol.locationType == LOCATIONTYPE.LocIsStatic:
            # static member
            s.append(CVACCESS_str(symbol.access) + ":")
            s.append("static")
            s.append(TypePrinter(self, name=self.name(symbol)).declare(symbol.type) + ";")
            s.append("//")
            s += self.metadata(symbol)
            s.append("//")
            s += TypePrinter(self).metadata(symbol.type)
        else:
            SymbolPrinter(self).debugSymbol(symbol)
            assert False, "TODO (DATAKIND." + DATAKIND_name(symbol.dataKind) + ",LOCATIONTYPE." + LOCATIONTYPE_name(symbol.locationType) + ")"
        return " ".join(s)


class EnumPrinter(SymbolPrinter):
    """I can declare and define enumerations."""

    def defaultOption(self, name):
        if name == "hexvalue": return True
        return None

    def validate(self, symbol):
        assert symbol.symTag == SYMTAG.SymTagEnum
        assert symbol.lexicalParent.symTag == SYMTAG.SymTagExe

    def declare(self, symbol):
        self.validate(symbol)
        s = []
        if symbol.constType: s.append("const")
        s.append("enum")
        s.append(symbol.name)
        return " ".join(s)

    def declareLine(self, symbol):
        return self.declare(symbol) + ";"

    def defineLines(self, symbol):
        #DEBUG("EnumPrinter.defineLines")
        #self.debugSymbol(symbol)
        self.validate(symbol)  
        lines = []
        lines.append(" ".join([self.declare(symbol), "//"] + self.metadata(symbol)))
        lines.append("{")
        children = DiaEnumSymbolsIterator(symbol.findChildrenEx(SYMTAG.SymTagNull, None, 0))
        hexvalue = self.option("hexvalue")
        for child in children:
            #SymbolPrinter(self).debugSymbol(child)
            assert child.symTag == SYMTAG.SymTagData
            assert child.access == 0
            assert child.addressOffset == 0
            assert child.addressSection == 0
            assert child.addressTaken == 0
            assert child.bitPosition == 0
            assert child.compilerGenerated == 0
            assert child.constType == 0
            assert child.dataKind == DATAKIND.DataIsConstant
            assert child.isAggregated == 0
            assert child.isSplitted == 0
            assert child.length == 0
            assert child.locationType == LOCATIONTYPE.LocIsConstant
            assert child.offset == 0
            assert child.registerId == 0
            assert child.relativeVirtualAddress == 0
            assert child.slot == 0
            assert child.token == 0
            assert child.unalignedType == 0
            assert child.virtualAddress == 0
            assert child.volatileType == 0
            assert child.type.symTag == SYMTAG.SymTagBaseType
            assert child.type.baseType == BASICTYPE.btInt # must be int type
            assert child.classParent.symTag == SYMTAG.SymTagEnum # must be enum symbol
            assert child.lexicalParent.symTag == SYMTAG.SymTagExe # must be global scope
            if hexvalue:
                value = hexValue(child.value, child.type.length)
            else:
                value = child.value
            lines.append("\t{} = {},".format(child.name, value))
        lines.append("};")
        return lines


class VTablePrinter(SymbolPrinter):
    """I can define vtables"""

    def validate(self, symbol):
        assert symbol.symTag == SYMTAG.SymTagVTable
        assert symbol.lexicalParent.symTag == SYMTAG.SymTagExe
        assert symbol.constType == 0
        assert symbol.unalignedType == 0
        assert symbol.volatileType == 0

    def defineLines(self, symbol):
        self.validate(symbol)
        self.debugSymbol(symbol)
        #for child in DiaEnumSymbolsIterator(symbol.findChildrenEx(SYMTAG.SymTagNull, None, 0)):
        #    DEBUG(".child")
        #    SymbolPrinter(self).debugSymbol(child)
        #DEBUG(".classParent")
        #SymbolPrinter(self).debugSymbol(symbol.classParent)
        #DEBUG(".type")
        #SymbolPrinter(self).debugSymbol(symbol.type)
        #for child in DiaEnumSymbolsIterator(symbol.type.findChildrenEx(SYMTAG.SymTagNull, None, 0)):
        #    DEBUG(".type.child")
        #    SymbolPrinter(self).debugSymbol(child)
        #DEBUG(".type.type")
        #SymbolPrinter(self).debugSymbol(symbol.type.type)
        #for child in DiaEnumSymbolsIterator(symbol.type.type.findChildrenEx(SYMTAG.SymTagNull, None, 0)):
        #    DEBUG(".type.type.child")
        #    SymbolPrinter(self).debugSymbol(child)
        #virtualFunctions = UdtPrinter(self).virtualFunctions(symbol.classParent)
        #assert symbol.type.symTag == SYMTAG.SymTagPointerType
        #assert symbol.type.type.symTag == SYMTAG.SymTagVTableShape
        #DEBUG("", len(virtualFunctions), symbol.type.type.count)
        #for function in virtualFunctions:
        #    SymbolPrinter(self).debugSymbol(function)
        #    DEBUG("virtualFunction", " ".join(SymbolPrinter(self).metadata(function)))
        #assert len(virtualFunctions) == symbol.type.type.count
        lines = []
        lines.append("// TODO " + " ".join(self.metadata(symbol)))
        for child in DiaEnumSymbolsIterator(symbol.findChildrenEx(SYMTAG.SymTagNull, None, 0)):
            lines.append("\t// TODO " + " ".join(SymbolPrinter(self).metadata(child)))
        return lines

class UdtPrinter(SymbolPrinter):
    """I print a struct/class/union definition."""

    def defaultOption(self, name):
        if name == "showHooks": return False
        assert False, "unexpected option '{}'".format(name)

    def validate(self, symbol):
        assert symbol.symTag in (SYMTAG.SymTagUDT, SYMTAG.SymTagBaseClass)
        assert symbol.lexicalParent.symTag == SYMTAG.SymTagExe

    def inheritance(self, baseClasses):
        ret = []
        for baseClass in baseClasses:
            s = []
            if baseClass.virtualBaseClass: s.append("virtual")
            s.append(CVACCESS_str(baseClass.access))
            s.append(baseClass.name)
            ret.append(" ".join(s))
        return ret

    def debugChildren(self, symbol, context=""):
        childrenSymbols = DiaEnumSymbolsIterator(symbol.findChildrenEx(SYMTAG.SymTagNull, None, 0))
        DEBUG(context + ".children", "len(childrenSymbols)={}".format(len(childrenSymbols)))
        for childSymbol in childrenSymbols:
            DEBUG(context + ".child")
            self.debugSymbol(childSymbol)

    def virtualFunctions(self, symbol):
        self.validate(symbol)
        #DEBUG("getVirtualFunctions", symbol, symbol.name, symbol.undecoratedName)
        #SymbolPrinter(self).debugSymbol(symbol)
        assert symbol.virtualBaseClass == 0 # TODO virtual base classes
        assert symbol.virtualBaseDispIndex == 0
        assert symbol.virtualBasePointerOffset == 0
        virtualFunctions = []
        for function in DiaEnumSymbolsIterator(symbol.findChildrenEx(SYMTAG.SymTagFunction, None, 0)):
            if function.virtual == 1 and function.intro == 1:
                #DEBUG("getVirtualFunctions", function, function.intro, function.virtualBaseOffset, function.name, function.undecoratedName)
                #self.debugSymbol(function)
                virtualFunctions.append(function)
        return virtualFunctions

    def defineVtableLines(self, symbol):
        assert symbol.symTag == SYMTAG.SymTagUDT
        assert symbol.udtKind == UDTKIND.UdtClass
        assert symbol.constType == 0
        assert symbol.unalignedType == 0
        assert symbol.volatileType == 0
        assert symbol.lexicalParent.symTag == SYMTAG.SymTagExe
        lines = []
        lines.append("struct vtable_t // const {}::`vftable'".format(symbol.name))
        lines.append("{")
        vtable = {}
        vtableSymbols = [symbol]
        while len(vtableSymbols) > 0:
            vtableSymbol = vtableSymbols[0]
            del vtableSymbols[0]
            vtableSymbols += list(DiaEnumSymbolsIterator(vtableSymbol.findChildrenEx(SYMTAG.SymTagBaseClass, None, 0)))
            #DEBUG("VTABLESYMBOL", vtableSymbol, vtableSymbol.name)
            for functionSymbol in self.virtualFunctions(vtableSymbol):
                assert functionSymbol.virtual == 1
                virtualBaseOffset = functionSymbol.virtualBaseOffset
                if not vtable.has_key(virtualBaseOffset) and functionSymbol.intro == 1:
                    vtable[virtualBaseOffset] = functionSymbol
        for virtualBaseOffset in sorted(vtable):
            functionSymbol = vtable[virtualBaseOffset]
            #name = functionSymbol.undecoratedName or "{}::{}".format(functionSymbol.classParent.name, functionSymbol.name)
            name = "{}::{}".format(functionSymbol.classParent.name, SymbolPrinter(self).name(functionSymbol))
            lines.append("\t/* vtable+{}/0x{:X} */ {} // {}".format(virtualBaseOffset, virtualBaseOffset, name, functionSymbol.undecoratedName))
        lines.append("};")
        return lines

    
    def declare(self, symbol):
        self.validate(symbol)
        s = []
        if symbol.constType:
            s.append("const")
        s.append(UDTKIND_str(symbol.udtKind))
        s.append(symbol.name)
        return " ".join(s)

    def declareLine(self, symbol):
        return self.declare(symbol) + ";"

    def declareEx(self, symbol, baseClasses):
        s = []
        # declare
        s.append(self.declare(symbol))
        # inheritance
        if len(baseClasses) > 0:
            s.append(":")
            s.append(", ".join(self.inheritance(baseClasses)))
        # metadata
        s.append("//")
        s += self.metadata(symbol)
        return " ".join(s)

    def declareMemberBaseclassOrVariable(self, symbol):
        symTag = symbol.symTag
        if symTag == SYMTAG.SymTagBaseClass:
            return "\t/* this+{} */ //{}: {} baseclass_{}; // {}".format(
                symbol.offset,
                CVACCESS_str(symbol.access),
                symbol.name,
                symbol.offset,
                " ".join(self.metadata(symbol)))
        elif symTag == SYMTAG.SymTagData:
            return "\t" + DataPrinter(self).declareMemberLine(symbol)
        else:
            DEBUG(".member")
            self.debugSymbol(symbol)
            return "\t// TODO {}".format(SYMTAG_name(symTag))

    def defineLines(self, symbol):
        self.validate(symbol)
        self.debugSymbol(symbol)
        className = self.name(symbol)
        baseClasses = [] # SymTagBaseClass
        vtables = [] # SymTagVTable
        nestedTypes = [] # SymTagEnum, SymTagUDT, SymTagTypedef
        variables = [] # SymTagData
        functions = [] # SymTagFunction
        # gather symbols
        children = DiaEnumSymbolsIterator(symbol.findChildrenEx(SYMTAG.SymTagNull, None, 0))
        DEBUG("UdtPrinter.defineLines", "len(children)={}".format(len(children)))
        for child in children:
            childSymTag = child.symTag
            if childSymTag == SYMTAG.SymTagBaseClass:
                baseClasses.append(child)
            elif childSymTag == SYMTAG.SymTagVTable:
                vtables.append(child)
            elif childSymTag in (SYMTAG.SymTagEnum, SYMTAG.SymTagUDT, SYMTAG.SymTagTypedef):
                nestedTypes.append(child)
            elif childSymTag == SYMTAG.SymTagData:
                variables.append(child)
            elif childSymTag == SYMTAG.SymTagFunction:
                functions.append(child)
            else:
                DEBUG(".child")
                self.debugSymbol(child)
                assert False, "TODO UdtPrinter.defineLines {}".format(SYMTAG_name(childSymTag))
        child = None
        lines = []
        # declare
        lines.append(self.declareEx(symbol, baseClasses))
        lines.append("{")
        # nested types (vtable, enum, udt, typedef)
        if symbol.udtKind == UDTKIND.UdtClass:
            lines.append("public:") # class is not public by default
        for child in vtables + nestedTypes:
            childSymTag = child.symTag
            if childSymTag == SYMTAG.SymTagEnum:
                lines += ["\t" + line for line in EnumPrinter(self).defineLines(child)]
            elif childSymTag == SYMTAG.SymTagVTable:
                lines += ["\t" + line for line in VTablePrinter(self).defineLines(child)]
            elif childSymTag == SYMTAG.SymTagUDT:
                lines += ["\t" + line for line in UdtPrinter(self).defineLines(child)]
            elif childSymTag == SYMTAG.SymTagTypedef:
                lines.append("\ttypedef {}; // {} // {}".format(
                    TypePrinter(self, name=child.name).declare(child.type),
                    " ".join(SymbolPrinter(self).metadata(child)),
                    " ".join(SymbolPrinter(self).metadata(child.type))))
            else:
                DEBUG(".child")
                self.debugSymbol(child)
                lines.append("\t// TODO " + " ".join(SymbolPrinter(self).metadata(child)))
            lines.append("")
        child = None
        # member variables
        if len(baseClasses) == 0 and len(vtables) > 0:
            lines.append("\t/* this+0 */ //const {}::`vftable'".format(className))
        for child in baseClasses + variables:
            lines.append(self.declareMemberBaseclassOrVariable(child))
        if len(baseClasses) + len(variables) > 0:
            lines.append("");
        # member functions
        for function in functions:
            lines.append("\t" + FunctionPrinter(self, className=className).declareMemberLine(function))
        # hooks
        if self.option("showHooks"):
            lines += ["", "private:"]
            hooks = [(function, FunctionPrinter(self).name(function)) for function in functions]
            def hookFilter(hook):
                function, name = hook
                if function.compilerGenerated: return None # ignore generated functions
                if function.constructor or name == className: return None # ignore constructors
                if name.startswith("~"): return None # ignore destructors
                return hook
            hooks = filter(hookFilter, hooks)
            for hook in hooks:
                function, name = hook
                DEBUG("", function, name)
                matches = [h for h in hooks if h[1] == name]
                if len(matches) > 1:
                    DEBUG("",hook)
                    DEBUG("",matches)
                    name = name + "_overload" + str(matches.index(hook) + 1)
                lines.append("\t static hook_method<{}> {};".format(
                    FunctionPrinter(self).declareMemberPointer(function),
                    "_" + name))
        lines.append("};")
        return lines

    def debugUDT(self, symbol):
        assert symbol.symTag == SYMTAG.SymTagUDT
        assert symbol.udtKind == UDTKIND.UdtClass
        assert symbol.constType == 0
        assert symbol.unalignedType == 0
        assert symbol.volatileType == 0
        assert symbol.lexicalParent.symTag == SYMTAG.SymTagExe
        self.debugSymbol(symbol)
        #vtable = self.getVtableFunctions(symbol)
        #for virtualBaseOffset in sorted(vtable):
        #    DEBUG("this+{}".format(virtualBaseOffset))
        #    self.debugSymbol(vtable[virtualBaseOffset])
        #return
        childSymbols = DiaEnumSymbolsIterator(symbol.findChildrenEx(SYMTAG.SymTagNull, None, 0))
        DEBUG("UdtPrinter.printVtable", "len(vtableSymbols)={}".format(len(childSymbols)))
        for childSymbol in childSymbols:
            childSymTag = childSymbol.symTag
            
            if childSymTag == SYMTAG.SymTagVTable:# vtable
                vtableSymbol = childSymbol
                DEBUG("")
                self.debugSymbol(vtableSymbol)
                self.debugChildren(vtableSymbol)

                typeSymbol = vtableSymbol.type # vtable pointer
                assert typeSymbol.symTag == SYMTAG.SymTagPointerType
                assert typeSymbol.constType == 0
                assert typeSymbol.length == 4
                assert typeSymbol.reference == 0
                assert typeSymbol.unalignedType == 0
                assert typeSymbol.volatileType == 0
                assert typeSymbol.lexicalParent.symTag == SYMTAG.SymTagExe
                DEBUG(".type")
                self.debugSymbol(typeSymbol)
                self.debugChildren(typeSymbol, ".type")

                shapeSymbol = typeSymbol.type # vtable shape
                assert shapeSymbol.symTag == SYMTAG.SymTagVTableShape
                assert shapeSymbol.constType == 0
                assert shapeSymbol.unalignedType == 0
                assert shapeSymbol.volatileType == 0
                assert shapeSymbol.lexicalParent.symTag == SYMTAG.SymTagExe
                DEBUG(".type.shape")
                self.debugSymbol(shapeSymbol)
                self.debugChildren(shapeSymbol, ".type.shape")
            elif childSymTag == SYMTAG.SymTagFunction and childSymbol.virtual == 1:
                #DEBUG("")
                #self.debugSymbol(childSymbol)
                pass
            elif childSymTag == SYMTAG.SymTagBaseClass:
                baseclassSymbol = childSymbol
                DEBUG(".baseclass")
                self.debugSymbol(baseclassSymbol)
                self.debugChildren(baseclassSymbol, ".baseclass")
            else:
                #DEBUG("")
                #self.debugSymbol(childSymbol)
                pass


class DiaSymbol:
    """Any symbol."""
    attributes = ("access","addressOffset","addressSection","addressTaken","age",
                  "arrayIndexType","arrayIndexTypeId","backEndBuild","backEndMajor","backEndMinor",
                  "backEndQFE","baseType","bitPosition","callingConvention","classParent",
                  "classParentId","code","compilerGenerated","compilerName","constType",
                  "constructor","container","count","countLiveRanges","customCallingConvention",
                  "dataKind","editAndContinueEnabled","farReturn","framePointerPresent","frontEndBuild",
                  "frontEndMajor","frontEndMinor","frontEndQFE","function","guid",
                  "hasAlloca","hasAssignmentOperator","hasCastOperator","hasDebugInfo","hasEH",
                  "hasEHa","hasInlAsm","hasLongJump","hasManagedCode","hasNestedTypes",
                  "hasSEH","hasSecurityChecks","hasSetJump","hfaDouble","hfaFloat",
                  "indirectVirtualBaseClass","inlSpec","interruptReturn","intrinsic","intro",
                  "isAggregated","isCTypes","isCVTCIL","isConstructorVirtualBase","isCxxReturnUdt",
                  "isDataAligned","isHotpatchable","isLTCG","isMSILNetmodule","isNaked",
                  "isSafeBuffers","isSplitted","isStatic","isStripped","language",
                  "length","lexicalParent","lexicalParentId","libraryName","liveRangeLength",
                  "liveRangeStartAddressOffset","liveRangeStartAddressSection","liveRangeStartRelativeVirtualAddress","localBasePointerRegisterId","locationType",
                  "lowerBound","lowerBoundId","machineType","managed","msil",
                  "name","nested","noInline","noReturn","noStackOrdering",
                  "notReached","objectPointerType","oemId","oemSymbolId","offset",
                  "offsetInUdt","optimizedCodeDebugInfo","overloadedOperator","packed","paramBasePointerRegisterId",
                  "platform","pure","rank","reference","registerId",
                  "relativeVirtualAddress","scoped","sealed","signature","slot",
                  "sourceFileName","strictGSCheck","symIndexId","symTag","symbolsFileName",
                  "targetOffset","targetRelativeVirtualAddress","targetSection","targetVirtualAddress","thisAdjust",
                  "thunkOrdinal","timeStamp","token","type","typeId",
                  "udtKind","unalignedType","undecoratedName","unmodifiedType","unused",
                  "upperBound","upperBoundId","value","virtual","virtualAddress",
                  "virtualBaseClass","virtualBaseDispIndex","virtualBaseOffset","virtualBasePointerOffset","virtualBaseTableType",
                  "virtualTableShape","virtualTableShapeId","volatileType","wasInlined")
    pydia = None
    symbol = None

    def __init__(self, pydia, symbol):
        self.pydia = pydia
        self.symbol = symbol

    def debug(self):
        context = self.__class__.__name__
        symbol = self.symbol
        DEBUG(context, symbol)
        for attr in self.attributes:
            try:
                result = getattr(self.symbol, attr)
            except comtypes.COMError, e:
                result = e
            DEBUG(context, attr, result)

    def declare(self):
        symbolClasses = {
            SYMTAG.SymTagArrayType: DiaArrayType,
            SYMTAG.SymTagBaseType: DiaBaseType,
            SYMTAG.SymTagData: DiaData,
            SYMTAG.SymTagEnum: DiaEnum,
            SYMTAG.SymTagFunctionType: DiaFunctionType,
            SYMTAG.SymTagPointerType: DiaPointerType,
            SYMTAG.SymTagUDT: DiaUDT,
            }
        symTag = self.symbol.symTag
        if symbolClasses.has_key(symTag):
            symbolClass = symbolClasses[symTag]
        else:
            err = "<TODO DiaSymbol.declare for symTag {}>".format(symTag)
            #return err
            self.debug()
            assert False, err
        if symbolClass.declare == self.__class__.declare:
            raise NotImplementedError("{}.declare".format(symbolClass.__name__))
        return symbolClass(self.pydia,self.symbol).declare()

    def sizeof(self):
        symbolClasses = {
            SYMTAG.SymTagArrayType: DiaArrayType,
            SYMTAG.SymTagBaseType: DiaBaseType,
            SYMTAG.SymTagEnum: DiaEnum,
            SYMTAG.SymTagPointerType: DiaPointerType,
            SYMTAG.SymTagUDT: DiaUDT,
            }
        symTag = self.symbol.symTag
        if symbolClasses.has_key(symTag):
            symbolClass = symbolClasses[symTag]
        else:
            err = "<TODO DiaSymbol.sizeof for symTag {}>".format(symTag)
            #return err
            self.debug()
            assert False, err
        if symbolClass.sizeof == self.__class__.sizeof:
            raise NotImplementedError("{}.sizeof".format(symbolClass.__name__))
        return symbolClass(self.pydia,self.symbol).sizeof()


class DiaFunctionType(DiaSymbol):
    """Each unique function signature is identified by a SymTagFunctionType symbol.
    Each parameter is identified as a class child symbol with a SymTagFunctionArgType tag."""
    attributes = ("callingConvention","classParent","classParentId","constType","count",
                  "lexicalParent","lexicalParentId","objectPointerType","symIndexId","symTag",
                  "thisAdjust","type","typeId","unalignedType","volatileType")

    def __init__(self, pydia, symbol):
        DiaSymbol.__init__(self,pydia,symbol)
        self.debug()

class DiaFunction(DiaSymbol):
    """Each function is identified by a SymTagFunction symbol."""
    attributes = ("access","addressOffset","addressSection","classParent","classParentId",
                  "constType","customCallingConvention","farReturn","hasAlloca","hasEH",
                  "hasEHa","hasInlAsm","hasLongJump","hasSecurityChecks","hasSEH",
                  "hasSetJump","interruptReturn","intro","InlSpec","isNaked",
                  "isStatic","length","lexicalParent","lexicalParentId","locationType",
                  "name","noInline","notReached","noReturn","noStackOrdering",
                  "optimizedCodeDebugInfo","pure","relativeVirtualAddress","symIndexId","symTag",
                  "token","type","typeId","unalignedType","undecoratedName",
                  "undecoratedNameEx","virtual","virtualAddress","virtualBaseOffset","volatileType")

    def __init__(self, pydia, symbol):
        DiaSymbol.__init__(self,pydia,symbol)
        assert symbol.symTag == SYMTAG.SymTagFunction
        self.debug()

class DiaTypedef(DiaSymbol):
    """Symbols with SymTagTypedef tags introduce names for other types."""
    attributes = ("baseType","classParent","classParentId","constructor","constType",
                  "hasAssignmentOperator","hasCastOperator","hasNestedTypes","length","lexicalParent",
                  "lexicalParentId","name","nested","overloadedOperator","packed",
                  "reference","scoped","symIndexId","symTag","type",
                  "typeId","udtKind","unalignedType","virtualTableShape","virtualTableShapeId",
                  "volatileType")

    def __init__(self, pydia, symbol):
        DiaSymbol.__init__(self,pydia,symbol)
        assert symbol.symTag == SYMTAG.SymTagTypedef
        self.debug()

class DiaBaseClass(DiaSymbol):
    """Each base class for a user-defined type (UDT) symbol is identified by a child with a SymTagBaseClass tag.
    The IDiaSymbol::get_type property contains the symbol for the underlying UDT,
    and all properties of the underlying UDT are available as part of this BaseClass symbol."""
    attributes = ("access","classParent","classParentId","constructor","constType",
                  "hasAssignmentOperator","hasCastOperator","hasNestedTypes","indirectVirtualBaseClass","length",
                  "lexicalParent","lexicalParentId","name","nested","offset",
                  "overloadedOperator","packed","scoped","symIndexId","symTag",
                  "type","typeId","udtKind","unalignedType","virtualBaseClass",
                  "virtualBaseDispIndex","virtualBasePointerOffset","virtualBaseTableType","virtualTableShape","virtualTableShapeId",
                  "volatileType")
    udtKindStr = {
        UDTKIND.UdtStruct: "struct",
        UDTKIND.UdtClass: "class",
        UDTKIND.UdtUnion: "union",
        }
    classParentSymbol = None
    constructor = None
    hasAssignmentOperator = None
    hasNestedTypes = None
    length = None
    name = None
    nested = None
    offset = None
    overloadedOperator = None
    typeSymbol = None
    udtKind = None
    virtualTableShapeSymbol = None

    def __init__(self, pydia, symbol):
        DiaSymbol.__init__(self,pydia,symbol)
        assert symbol.symTag == SYMTAG.SymTagBaseClass
        assert symbol.access == CVACCESS.CV_public
        assert symbol.constType == 0
        assert symbol.hasCastOperator == 0
        assert symbol.indirectVirtualBaseClass == 0
        assert symbol.lexicalParent.symTag == SYMTAG.SymTagExe
        assert symbol.packed == 0
        assert symbol.scoped == 0
        assert symbol.unalignedType == 0
        assert symbol.virtualBaseClass == 0
        assert symbol.virtualBaseDispIndex == 0
        assert symbol.virtualBasePointerOffset == 0
        assert not symbol.virtualBaseTableType #<POINTER(IDiaSymbol) ptr=0x0 at 486bc60>
        assert symbol.volatileType == 0

        self.classParentSymbol = symbol.classParent
        self.constructor = symbol.constructor
        self.hasAssignmentOperator = symbol.hasAssignmentOperator
        self.hasNestedTypes = symbol.hasNestedTypes
        self.length = symbol.length
        self.name = symbol.name
        self.nested = symbol.nested
        self.offset = symbol.offset
        self.overloadedOperator = symbol.overloadedOperator
        self.typeSymbol = symbol.type
        self.udtKind = symbol.udtKind
        self.virtualTableShape = symbol.virtualTableShape

    def define(self):
        return "/* this+{} */ public: //{} {}".format(
            self.offset,
            self.udtKindStr[self.udtKind],
            self.name);

class DiaData(DiaSymbol):
    """TODO"""
    attributes = ("access","addressOffset","addressSection","addressTaken","bitPosition",
                  "classParent","classParentId","compilerGenerated","constType","dataKind",
                  "isAggregated","isSplitted","length","lexicalParent","lexicalParentId",
                  "locationType","name","offset","registerId","relativeVirtualAddress",
                  "slot","symIndexId","symTag","token","type",
                  "typeId","unalignedType","value","virtualAddress","volatileType")
    accessStr = {
        CVACCESS.CV_private: "private:",
        CVACCESS.CV_protected: "protected:",
        CVACCESS.CV_public: "public:",
        }
    location = {# (dataKind,locationType) -> (declare,define)
        # // source(define)
        # static int test_location_static = 1;
        (DATAKIND.DataIsFileStatic,LOCATIONTYPE.LocIsStatic): ("source","source"),
        # // source(define)
        # const int test_location_const = 1;
        # static const int test_location_static_const = 1;
        (DATAKIND.DataIsConstant,LOCATIONTYPE.LocIsConstant): ("source","source"),
        # // header(declare)
        # extern int test_location_extern;
        # extern const int test_location_extern_const;
        # // header(declare inside TestClass)
        #            static       int TestClass::test_location_class_default_static;
        #            static const int TestClass::test_location_class_default_static_const;
        # private:   static       int TestClass::test_location_class_private_static;
        # private:   static const int TestClass::test_location_class_private_static_const;
        # protected: static       int TestClass::test_location_class_protected_static;
        # protected: static const int TestClass::test_location_class_protected_static_const;
        # public:    static       int TestClass::test_location_class_public_static;
        # public:    static const int TestClass::test_location_class_public_static_const;
        # // source(define)
        #       int test_location = 1;
        #       int test_location_extern = 1;
        # const int test_location_extern_const = 1;
        #       int TestClass::test_location_class_default_static = 1;
        # const int TestClass::test_location_class_default_static_const = 1;
        #       int TestClass::test_location_class_private_static = 1;
        # const int TestClass::test_location_class_private_static_const = 1;
        #       int TestClass::test_location_class_protected_static = 1;
        # const int TestClass::test_location_class_protected_static_const = 1;
        # const int TestClass::test_location_class_public_static_const = 1;
        #       int TestClass::test_location_class_public_static = 1;
        (DATAKIND.DataIsGlobal,LOCATIONTYPE.LocIsStatic): ("header/source","source"),
        }
    access = None # 0 in global scope, valid otherwise
    addressOffset = None
    addressSection = None
    classParentSymbol = None
    dataKind = None
    locationType = None
    name = None
    offset = None
    typeSymbol = None
    relativeVirtualAddress = None
    value = None
    virtualAddress = None

    def __init__(self, pydia, symbol):
        DiaSymbol.__init__(self,pydia,symbol)
        assert symbol.symTag == SYMTAG.SymTagData
        #DEBUG("")
        #self.debug()
        assert symbol.addressTaken == 0
        assert symbol.bitPosition == 0
        assert symbol.compilerGenerated == 0
        assert symbol.constType == 0
        assert symbol.isAggregated == 0
        assert symbol.isSplitted == 0
        assert symbol.length == 0
        assert symbol.lexicalParent.symTag == SYMTAG.SymTagExe # must be global scope
        assert symbol.registerId == 0
        assert symbol.slot == 0
        assert symbol.token == 0
        assert symbol.unalignedType == 0
        assert symbol.volatileType == 0

        self.access = symbol.access
        self.addressOffset = symbol.addressOffset
        self.addressSection = symbol.addressSection
        self.classParentSymbol = symbol.classParent
        self.dataKind = symbol.dataKind
        self.locationType = symbol.locationType
        self.name = symbol.name
        self.offset = symbol.offset
        self.typeSymbol = symbol.type
        self.relativeVirtualAddress = symbol.relativeVirtualAddress
        self.value = symbol.value
        self.virtualAddress = symbol.virtualAddress

    def declare(self):
        assert self.access != 0
        return "/* this+{}/{:x} */ {} {} {};".format(
            self.offset,
            self.offset,
            self.accessStr[self.access],
            DiaSymbol(self.pydia,self.typeSymbol).declare(),
            self.name)

    def defineLines(self):
        lines = []
        if self.locationType == LOCATIONTYPE.LocIsConstant and self.dataKind == DATAKIND.DataIsConstant:
            # constant variable present only inside a source file; can be static or not
            #   const int test_location_const = 1;
            #   static const int test_location_static_const = 1;
            typeStr = DiaSymbol(self.pydia,self.typeSymbol).declare()
            hexValueStr = hexValue(self.value,self.sizeof())
            lines.append("{} {} = {};//{} <constant> <maybe-static>".format(
                typeStr, self.name, self.value, hexValueStr))
        elif self.locationType == LOCATIONTYPE.LocIsStatic:
            comments = [
                "<va={}>".format(hexValue(self.virtualAddress,8)),
                "<rva={}>".format(hexValue(self.relativeVirtualAddress,8)),
                "<section={}>".format(hexValue(self.addressSection,4)),
                "<offset={}>".format(hexValue(self.addressOffset,8)),
                ]
            if self.dataKind == DATAKIND.DataIsFileStatic:
                # non-constant static variable inside a source file
                # (source file)
                # static int test_location_static = 1;
                dataKindStr = "static "
            elif self.dataKind == DATAKIND.DataIsGlobal:
                # normal or extern variable inside a source file
                # (source file)
                #       int test_location = 1;
                #       int test_location_extern = 1;
                # const int test_location_extern_const = 1;
                #       int TestClass::test_location_class_default_static = 1;
                # const int TestClass::test_location_class_default_static_const = 1;
                #       int TestClass::test_location_class_private_static = 1;
                # const int TestClass::test_location_class_private_static_const = 1;
                #       int TestClass::test_location_class_protected_static = 1;
                # const int TestClass::test_location_class_protected_static_const = 1;
                # const int TestClass::test_location_class_public_static_const = 1;
                #       int TestClass::test_location_class_public_static = 1;
                # (header file inside TestClass)
                #            static       int TestClass::test_location_class_default_static;
                #            static const int TestClass::test_location_class_default_static_const;
                # private:   static       int TestClass::test_location_class_private_static;
                # private:   static const int TestClass::test_location_class_private_static_const;
                # protected: static       int TestClass::test_location_class_protected_static;
                # protected: static const int TestClass::test_location_class_protected_static_const;
                # public:    static       int TestClass::test_location_class_public_static;
                # public:    static const int TestClass::test_location_class_public_static_const;
                dataKindStr = ""#"extern "
                comments.append("<normal-or-extern-or-member-static>")
            else:
                dataKindStr = "<{}> ".format(DATAKIND_name(self.dataKind))
            typeStr = DiaSymbol(self.pydia,self.typeSymbol).declare()
            lines.append('{}& {} = VTOR<int>(SymDB::Add("{}", SAKEXE, "{}")); // = TODO;'.format(
                typeStr, self.name, self.name, self.name))
            lines.append("{}{} {};// {}".format(
                dataKindStr, typeStr, self.name, ' '.join(comments)))
        else:
            #self.debug()
            #DiaSymbol(self.pydia,self.typeSymbol).debug()
            lines.append("<TODO DiaData.define {}>".format(
                (LOCATIONTYPE_name(self.locationType),DATAKIND_name(self.dataKind))))
        return lines

    def sizeof(self):
        return DiaSymbol(self.pydia,self.typeSymbol).sizeof()

class DiaFunctionType(DiaSymbol):
    """TODO"""
    attributes = ("callingConvention","classParent","classParentId","constType","count",
                  "lexicalParent","lexicalParentId","objectPointerType","symIndexId","symTag",
                  "thisAdjust","type","typeId","unalignedType","volatileType")
    callingConvention = None
    classParentSymbol = None # None or UDT
    objectPointerTypeSymbol = None # None or PointerType
    count = None
    thisAdjust = None
    returnType = None

    def __init__(self, pydia, symbol):
        DiaSymbol.__init__(self,pydia,symbol)
        #DEBUG("")
        #self.debug()
        assert symbol.symTag == SYMTAG.SymTagFunctionType
        assert symbol.constType == 0
        assert symbol.lexicalParent.symTag == SYMTAG.SymTagExe # must be global scope
        classParent = symbol.classParent
        if classParent:
            assert classParent.symTag == SYMTAG.SymTagUDT
        objectPointerType = symbol.objectPointerType
        if objectPointerType:
            assert objectPointerType.symTag == SYMTAG.SymTagPointerType
        assert symbol.unalignedType == 0
        assert symbol.volatileType == 0

        self.callingConvention = symbol.callingConvention
        classParent = symbol.classParent
        if classParent:
            self.classParentSymbol = classParent
        self.count = symbol.count
        objectPointerType = symbol.objectPointerType
        if objectPointerType:
            self.objectPointerTypeSymbol = objectPointerType
        self.thisAdjust = symbol.thisAdjust
        self.returnType = symbol.type

    def declare(self):
        #self.debug()
        #assert False, "<TODO DiaFunctionType.declare>"
        return "<TODO DiaFunctionType.declare>"

    def sizeof(self):
        return 


class DiaUDT(DiaSymbol):
    """TODO"""
    attributes = ("classParent","classParentId","constructor","constType","hasAssignmentOperator",
                  "hasCastOperator","hasNestedTypes","length","lexicalParent","lexicalParentId",
                  "name","nested","overloadedOperator","packed","scoped",
                  "symIndexId","symTag","udtKind","unalignedType","virtualTableShape",
                  "virtualTableShapeId","volatileType")
    udtKindStr = {
        UDTKIND.UdtStruct: "struct",
        UDTKIND.UdtClass: "class",
        UDTKIND.UdtUnion: "union",
        }
    classParentSymbol = None
    constructor = None
    constType = None
    hasAssignmentOperator = None
    hasCastOperator = None
    hasNestedTypes = None
    length = None
    name = None
    nested = None
    overloadedOperator = None
    packed = None
    scoped = None
    udtKind = None
    virtualTableShapeSymbol = None
    volatileType = None

    def __init__(self, pydia, symbol):
        DiaSymbol.__init__(self,pydia,symbol)
        #DEBUG("")
        #self.debug()
        assert symbol.symTag == SYMTAG.SymTagUDT
        assert symbol.lexicalParent.symTag == SYMTAG.SymTagExe # must be global scope
        assert symbol.unalignedType == 0

        self.classParentSymbol = symbol.classParent
        self.constructor = symbol.constructor
        self.constType = symbol.constType
        self.hasAssignmentOperator = symbol.hasAssignmentOperator
        self.hasCastOperator = symbol.hasCastOperator
        self.hasNestedTypes = symbol.hasNestedTypes
        self.length = symbol.length
        self.name = symbol.name
        self.nested = symbol.nested
        self.overloadedOperator = symbol.overloadedOperator
        self.scoped = symbol.scoped
        self.udtKind = symbol.udtKind
        self.packed = symbol.packed
        self.virtualTableShapeSymbol = symbol.virtualTableShape
        self.volatileType = symbol.volatileType

    def declare(self):
        s = []
        if self.constructor:            s.append("<constructor>")
        if self.hasAssignmentOperator:  s.append("<hasAssignmentOperator>")
        if self.hasCastOperator:        s.append("<hasCastOperator>")
        if self.hasNestedTypes:         s.append("<hasNestedTypes>")
        if self.nested:                 s.append("<nested>")
        if self.overloadedOperator:     s.append("<overloadedOperator>")
        if self.packed:                 s.append("<packed>")
        if self.scoped:                 s.append("<scoped>")
        if self.volatileType:           s.append("<volatileType>")
        if self.constType:              s.append("const")
        s.append(self.udtKindStr[self.udtKind])
        s.append(self.name)
        return ' '.join(s)

    def defineLines(self):
        baseClassSymbols = []
        nestedSymbols = []
        dataSymbols = []
        functionSymbols = []
        
        self.debug()
        children = self.pydia.findChildrenEx(self.symbol)
        DEBUG("DiaUDT.defineLines", "len(children) == {}".format(len(children)))
        for child in children:
            childSymTag = child.symTag
            if childSymTag == SYMTAG.SymTagBaseClass:
                baseClassSymbols.append(child)
            elif childSymTag == SYMTAG.SymTagEnum or childSymTag == SYMTAG.SymTagUDT:
                nestedSymbols.append(child)
            elif childSymTag == SYMTAG.SymTagData:
                dataSymbols.append(child)
                #DEBUG("")
                #DiaData(self.pydia,child).debug()
                #lines.append("\t" + DiaData(self.pydia,child).declare())
            elif childSymTag == SYMTAG.SymTagFunction:
                functionSymbols.append(child)
            else:
                pass
                DEBUG("")
                DiaSymbol(self.pydia,child).debug()
        lines = []
        if len(baseClassSymbols) > 0:
            lines.append(self.declare() + " : " + ','.join([baseClass.name for baseClass in baseClassSymbols]))
        else:
            lines.append(self.declare())
        lines.append("{")
        for symbol in nestedSymbols:
            if symbol.symTag == SYMTAG.SymTagEnum:
                mylines = DiaEnum(self.pydia,symbol).defineLines()
            else:#if symbol.symTag == SYMTAG.SymTagUDT:
                mylines = DiaUDT(self.pydia,symbol).defineLines()
            lines += ["\t" + line for line in mylines]
            lines.append("")
        for i in xrange(len(baseClassSymbols)):
            symbol = baseClassSymbols[i]
            lines += ["\t" + DiaBaseClass(self.pydia,symbol).define() + " baseclass_"+ str(i) + ";"]
        for symbol in dataSymbols:
            lines.append("\t" + DiaData(self.pydia,symbol).declare())
        for symbol in functionSymbols:
            lines.append("\t//FUNCTION {} // {}".format(symbol.name, symbol.undecoratedName))
        lines.append("};")
        return lines
        assert False, "<TODO DiaUDT.defineLines>"

    def sizeof(self):
        return self.length


class DiaPointerType(DiaSymbol):
    """Pointer type."""
    attributes = ("constType","length","lexicalParent","lexicalParentId","reference",
                  "symIndexId","symTag","type","typeId","unalignedType",
                  "volatileType")
    constType = None
    reference = None
    typeSymbol = None
    volatileType = None

    def __init__(self, pydia, symbol):
        DiaSymbol.__init__(self,pydia,symbol)
        assert symbol.symTag == SYMTAG.SymTagPointerType
        assert symbol.length == 4
        assert symbol.lexicalParent.symTag == SYMTAG.SymTagExe # must be global scope
        assert symbol.unalignedType == 0

        self.constType = symbol.constType
        self.reference = symbol.reference
        self.typeSymbol = symbol.type
        self.volatileType = symbol.volatileType

    def declare(self):
        s = []
        s.append(DiaSymbol(self.pydia,self.typeSymbol).declare())
        if self.reference:      s.append("&")
        else:                   s.append("*")
        if self.constType:      s.append("const")
        if self.volatileType:   s.append("<volatileType>")
        return ''.join(s)

    def sizeof(self):
        return 4


class DiaArrayType(DiaSymbol):
    """Array type."""
    attributes = ("arrayIndexType","arrayIndexTypeId","constType","count","length",
                  "lexicalParent","lexicalParentId","rank","symIndexId","symTag",
                  "type","typeId","unalignedType","volatileType")
    count = None
    length = None
    typeSymbol = None

    def __init__(self, pydia, symbol):
        DiaSymbol.__init__(self,pydia,symbol)
        assert symbol.symTag == SYMTAG.SymTagArrayType
        arrayIndexType = symbol.arrayIndexType
        printer = SymbolPrinter(pydia)
        printer.debugSymbol(symbol)
        printer.debugSymbol(arrayIndexType)
        del printer
        assert arrayIndexType.symTag == SYMTAG.SymTagBaseType
        assert arrayIndexType.baseType in (BASICTYPE.btULong, BASICTYPE.btInt) # integer index
        assert symbol.constType == 0
        assert symbol.lexicalParent.symTag == SYMTAG.SymTagExe # must be global scope
        assert symbol.rank == 0
        assert symbol.unalignedType == 0
        assert symbol.volatileType == 0

        self.count = symbol.count
        self.length = symbol.length
        self.typeSymbol = symbol.type

    def declare(self):
        s = []
        s.append(DiaSymbol(self.pydia,self.typeSymbol).declare())
        s.append("[{}]".format(self.count))
        return ''.join(s)

    def sizeof(self):
        return self.length


class DiaEnumData(DiaSymbol): # done
    """Enum value.
    Parent: DiaEnum"""
    attributes = ("access", "addressOffset", "addressSection", "addressTaken", "bitPosition",
                  "classParent", "classParentId", "compilerGenerated", "constType", "dataKind",
                  "isAggregated", "isSplitted", "length", "lexicalParent", "lexicalParentId",
                  "locationType", "name", "offset", "registerId", "relativeVirtualAddress",
                  "slot", "symIndexId", "symTag", "token", "type",
                  "typeId", "unalignedType", "value", "virtualAddress", "volatileType")
    name = None
    value = None
    
    def __init__(self, pydia, symbol):
        DiaSymbol.__init__(self,pydia,symbol)
        assert symbol.symTag == SYMTAG.SymTagData
        assert symbol.access == 0
        assert symbol.addressOffset == 0
        assert symbol.addressSection == 0
        assert symbol.addressTaken == 0
        assert symbol.bitPosition == 0
        assert symbol.compilerGenerated == 0
        assert symbol.constType == 0
        assert symbol.dataKind == DATAKIND.DataIsConstant
        assert symbol.isAggregated == 0
        assert symbol.isSplitted == 0
        assert symbol.length == 0
        assert symbol.locationType == LOCATIONTYPE.LocIsConstant
        assert symbol.offset == 0
        assert symbol.registerId == 0
        assert symbol.relativeVirtualAddress == 0
        assert symbol.slot == 0
        assert symbol.token == 0
        assert symbol.unalignedType == 0
        assert symbol.virtualAddress == 0
        assert symbol.volatileType == 0
        symbolType = symbol.type
        assert symbolType.symTag == SYMTAG.SymTagBaseType
        assert symbolType.baseType == BASICTYPE.btInt # must be int type
        assert symbol.classParent.symTag == SYMTAG.SymTagEnum # must be enum symbol
        assert symbol.lexicalParent.symTag == SYMTAG.SymTagExe # must be global scope
        
        self.name = symbol.name
        self.value = symbol.value

    def define(self, prefix="", suffix=",", hexvalue=True):
        assert isinstance(prefix, str)
        assert isinstance(suffix, str)
        assert hexvalue in (True, False)
        if hexvalue:
            value = "0x%X" % (self.value&0xFFFFFFFF)
        else:
            value = self.value
        s = "{}{} = {}{}".format(prefix, self.name, value, suffix)
        return s


class DiaEnum(DiaSymbol): # done
    """Enum type.
    If nested, define inside the parent instead of globally.
    Child: DiaEnumData"""
    attributes = ("baseType", "classParent", "classParentId", "constructor", "constType",
                  "hasAssignmentOperator", "hasCastOperator", "hasNestedTypes", "length", "lexicalParent",
                  "lexicalParentId", "name", "nested", "overloadedOperator", "packed",
                  "scoped", "symIndexId", "symTag", "type", "typeId",
                  "unalignedType", "volatileType")
    constType = None
    classParentSymbol = None # when child
    name = None
    nested = None

    def __init__(self, pydia, symbol):
        DiaSymbol.__init__(self,pydia,symbol)
        assert symbol.symTag == SYMTAG.SymTagEnum
        assert symbol.baseType == BASICTYPE.btInt
        assert symbol.constructor == 0
        assert symbol.hasAssignmentOperator == 0
        assert symbol.hasCastOperator == 0
        assert symbol.hasNestedTypes == 0
        assert symbol.length == 4
        assert symbol.overloadedOperator == 0
        assert symbol.packed == 0
        assert symbol.scoped == 0
        assert symbol.unalignedType == 0
        assert symbol.volatileType == 0
        symbolType = symbol.type
        assert symbolType.symTag == SYMTAG.SymTagBaseType
        assert symbolType.baseType == BASICTYPE.btInt # must be int type
        assert symbol.lexicalParent.symTag == SYMTAG.SymTagExe # must be global scope

        self.classParentSymbol = symbol.classParent
        self.constType = symbol.constType
        self.name = symbol.name
        self.nested = symbol.nested

    def children(self):
        return self.pydia.findChildrenEx(self.symbol)

    def declare(self):
        s = []
        if self.constType:
            s.append("const")
        s.append("enum")
        s.append(self.name)
        return ' '.join(s)

    def defineLines(self):
        lines = []
        lines.append(self.declare())
        s = "{"
        if self.nested:
            s += "//nested (put inside the parent)"
        lines.append(s)
        for child in self.children():
            enumData = DiaEnumData(self, child)
            lines.append(enumData.define(prefix="\t"))
        lines.append("};")
        return lines

    def sizeof(self):
        return 4


class DiaBaseType(DiaSymbol): # done
    """Compiler type."""
    attributes = ("baseType", "constType", "length", "lexicalParent", "lexicalParentId",
                  "symIndexId", "symTag", "unalignedType", "volatileType")
    typeStr = {
        (BASICTYPE.btVoid,0): "void", # void type
        (BASICTYPE.btChar,1): "char", # char WITHOUT signed/unsigned type
        (BASICTYPE.btWChar,2): "wchar_t", # wide character type
        (BASICTYPE.btInt,1): "signed char", # signed integer type EXCEPT long
        (BASICTYPE.btInt,2): "short",
        (BASICTYPE.btInt,4): "int",
        (BASICTYPE.btInt,8): "__int64", # (long long)
        (BASICTYPE.btUInt,1): "unsigned char", # unsigned integer type EXCEPT long
        (BASICTYPE.btUInt,2): "unsigned short",
        (BASICTYPE.btUInt,4): "unsigned int",
        (BASICTYPE.btUInt,8): "unsigned __int64", # (unsigned long long)
        (BASICTYPE.btFloat,4): "float", # floating-point number type
        (BASICTYPE.btFloat,8): "double",
        (BASICTYPE.btBool,1): "bool", # boolean type
        (BASICTYPE.btLong,4): "long", # signed long int type
        (BASICTYPE.btULong,4): "unsigned long", # unsigned long int type
        }
    baseType = None
    constType = None
    length = None
    unalignedType = None
    volatileType = None

    def __init__(self, pydia, symbol):
        DiaSymbol.__init__(self,pydia,symbol)
        assert symbol.symTag == SYMTAG.SymTagBaseType
        assert symbol.lexicalParent.symTag == SYMTAG.SymTagExe # must be the global scope

        self.baseType = symbol.baseType
        self.constType = symbol.constType
        self.length = symbol.length
        self.unalignedType = symbol.unalignedType
        self.volatileType = symbol.volatileType

    def declare(self):
        s = []
        if self.constType:      s.append("const")
        if self.unalignedType:  s.append("<unalignedType>")
        if self.volatileType:   s.append("volatile")
        s.append(self.typeStr[(self.baseType,self.length)])
        return ' '.join(s)

    def sizeof(self):
        return self.length


class DiaExe(DiaSymbol): # done
    """Executable.
    It represents the global scope."""
    attributes = ("age","guid","isCTypes","isStripped","machineType",
                  "name","signature","symbolsFileName","symIndexId","symTag")
    machineTypeStr = {
        0x014c: "IMAGE_FILE_MACHINE_I386",
        0x0200: "IMAGE_FILE_MACHINE_IA64",
        0x8664: "IMAGE_FILE_MACHINE_AMD64",
        }
    age = None
    guid = None # comtypes.GUID
    machineType = None
    name = None
    signature = None
    symbolsFileName = None

    def __init__(self, pydia, symbol):
        DiaSymbol.__init__(self,pydia,symbol)
        assert symbol.symTag == SYMTAG.SymTagExe
        assert symbol.isCTypes == 0
        assert symbol.isStripped == 0

        self.age = symbol.age
        self.guid = symbol.guid
        self.machineType = symbol.machineType
        self.name = symbol.name
        self.signature = symbol.signature
        self.symbolsFileName = symbol.symbolsFileName


class PyDia:
    msdiaFilepath = "msdia100.dll"
    searchPath = "SRV**\\\\symbols\\symbols"

    targetFilepath = None
    msdia = None # COM module
    dataSource = None # IDiaDataSource
    session = None # IDiaSession
    globalScope = None # IDiaSymbol

    prefix = []

    def __init__(self, targetFilepath):
        assert isinstance(targetFilepath, str)
        self.targetFilepath = targetFilepath

        DEBUG("PyDia","__enter__")
        self.msdia = GetModule(self.msdiaFilepath)
        DEBUG(self.msdiaFilepath, self.msdia)
        
        self.dataSource = CreateObject(self.msdia.DiaSource, interface=self.msdia.IDiaDataSource)
        DEBUG("DataSource", self.dataSource)

        if self.targetFilepath.lower().endswith(".exe"):
            self.dataSource.loadDataForExe(self.targetFilepath, self.searchPath, None)
        elif self.targetFilepath.lower().endswith(".pdb"):
            self.dataSource.loadDataFromPdb(self.targetFilepath)
        else:
            raise Error("Unknown file extension [{}]".format(self.targetFilepath))
        self.session = self.dataSource.openSession()
        DEBUG("Session", self.session)
        
        self.globalScope = self.session.globalScope
        DEBUG("GlobalScope", self.globalScope)

    def __del__(self):
        if self.globalScope is not None:
            del self.globalScope
        if self.dataSource is not None:
            del self.dataSource
        if self.msdia is not None:
            del self.msdia

    def push(self, s):
        """Append a section to the prefix."""
        self.prefix.append(str(s))

    def pop(self):
        """Remove the last section of the prefix."""
        del self.prefix[-1]

    def findChildrenEx(self, symbol=None):
        """Return an iterator for all the children."""
        if symbol == None:
            symbol = self.globalScope
        children = symbol.findChildrenEx(SYMTAG.SymTagNull, None, 0)
        return DiaEnumSymbolsIterator(children)

    def findChildrenByTypeEx(self, symTag, symbol=None):
        """Return an iterator for all the children of the specified type."""
        if symbol == None:
            symbol = self.globalScope
        children = symbol.findChildrenEx(symTag, None, 0)
        return DiaEnumSymbolsIterator(children)

    def findChildrenByNameEx(self, name, symTag=SYMTAG.SymTagNull, symbol=None):
        """Return an iterator for all the children of the specified type."""
        if symbol == None:
            symbol = self.globalScope
        children = symbol.findChildrenEx(symTag, name, 0)
        return DiaEnumSymbolsIterator(children)

    def printSession(self):
        context = "IDiaSession.getEnumTables"
        children = self.session.getEnumTables()
        DEBUG(context,"len(children) == {}".format(len(children)))
        DEBUG(context,children)
        for table in children:
            DEBUG(context,table)
            interfaces = [
                # TODO interfaces not public?
                #self.msdia.IDiaEnumSectionContribs,
                #self.msdia.IDiaEnumFrameData,
                self.msdia.IDiaEnumInjectedSources,
                self.msdia.IDiaEnumSourceFiles,
                ]
            for interface in [self.msdia.IDiaEnumSourceFiles]:
                try:
                    DEBUG(context,table.QueryInterface(interface))
                except:
                    pass
        context = "IDiaSession.findFile"
        children = self.session.findFile(None,None,0)
        DEBUG(context,"len(children) == {}".format(len(children)))
        DEBUG(context,children)
        for child in children:
            DEBUG(context,child)
            DEBUG(context,child.QueryInterface(self.msdia.IDiaSymbol))

    def printDatas(self):
        children = self.findChildrenByTypeEx(SYMTAG.SymTagData)
        DEBUG("PyDia.printDatas", "len(children)", len(children))
        lines = []
        skipped = 0
        bytype = {}
        for symbol in children:
            if symbol.type and symbol.type.symTag == SYMTAG.SymTagBaseType:
                DEBUG("", TypePrinter(self).declare(symbol.type), "//", " ".join(SymbolPrinter(self).metadata(symbol)), "//", " ".join(SymbolPrinter(self).metadata(symbol.type)))
            data = DiaData(self, symbol)
            if data.name.find("test_location") == -1:# or data.dataKind != DATAKIND.DataIsConstant:# skip
                skipped += 1
                continue
                pass
            #k = (data.dataKind,data.locationType)
            #v = data.declare()
            #try:
            #    bytype[k].append(v)
            #except KeyError:
            #    bytype[k] = [v]
            lines.append("")
            lines += data.defineLines()
            lines.append("sizeof({}) == {}".format(symbol.name, data.sizeof()))
            #break
        self._printLines(*lines)
        if skipped > 0:
            DEBUG("PyDia.printDatas", "skipped={}".format(skipped), "count={}".format(len(children)-skipped))
        #for k in bytype.keys():
        #    for v in bytype[k]:
        #        DEBUG(k, v)

    def printFunctionTypes(self):
        children = self.findChildrenByTypeEx(SYMTAG.SymTagFunctionType)
        DEBUG("PyDia.printFunctionTypes", "len(children)", len(children))
        lines = []
        for symbol in children:
            functionType = DiaFunctionType(self, symbol)
            s = functionType.declare()
            #n = functionType.sizeof()
            lines.append("")
            lines.append(s)
            #lines.append("sizeof({}) == {}".format(s,n))
            #assert False, "<TODO PyDia.printFunctionTypes>"
        self._printLines(*lines)

    def printUDTsByLength(self, length):
        children = self.findChildrenByTypeEx(SYMTAG.SymTagUDT)
        DEBUG("PyDia.printUDTs", "len(children)", len(children))
        lines = []
        skipped = 0
        udtPrinter = UdtPrinter(self)
        for symbol in children:
            if symbol.length != length:
                skipped += 1
                continue
            s = udtPrinter.declare(symbol)
            n = symbol.length
            lines += [
                "",
                s,
                "sizeof({}) == {}".format(s, n)]
            lines += udtPrinter.defineLines(symbol)
        del udtPrinter
        self._printLines(*lines)
        if skipped > 0:
            DEBUG("PyDia.printUDTsByLength", "skipped={}".format(skipped), "count={}".format(len(children)-skipped))

    def printUDT2(self, name):
        children = self.findChildrenByNameEx(name,SYMTAG.SymTagUDT)
        DEBUG("PyDia.printUDT", "len(children)", len(children))
        lines = []
        udtPrinter = UdtPrinter(self)
        for symbol in children:
            s = udtPrinter.declare(symbol)
            n = symbol.length
            lines += [
                "",
                s,
                "sizeof({}) == {}".format(s, n)]
            lines += udtPrinter.defineLines(symbol)
        del udtPrinter
        self._printLines(*lines)

    def printUDT(self, name):
        children = self.findChildrenByNameEx(name,SYMTAG.SymTagUDT)
        DEBUG("PyDia.printUDT", "len(children)", len(children))
        lines = []
        for symbol in children:
            udt = DiaUDT(self, symbol)
            s = udt.declare()
            n = udt.sizeof()
            lines += [
                "",
                s,
                "sizeof({}) == {}".format(s,n)]
            lines += udt.defineLines()
        self._printLines(*lines)

    def printVtable(self, name):
        children = self.findChildrenByNameEx(name,SYMTAG.SymTagUDT)
        DEBUG("PyDia.printVtable", "len(children)", len(children))
        lines = []
        for symbol in children:
            #UdtPrinter(self).debugSymbol(symbol)
            lines += UdtPrinter(self).defineVtableLines(symbol)
        self._printLines(*lines)

    def printUDTs(self):
        children = self.findChildrenByTypeEx(SYMTAG.SymTagUDT)
        DEBUG("PyDia.printUDTs", "len(children)", len(children))
        lines = []
        udtPrinter = UdtPrinter(self)
        for symbol in children:
            udt = DiaUDT(self, symbol)
            s = udtPrinter.declare(symbol)
            n = symbol.length
            lines += [
                "",
                s,
                "sizeof({}) == {}".format(s,n)]
            lines += udt.defineLines()
        del udtPrinter
        self._printLines(*lines)

    def printPointerTypes(self):
        children = self.findChildrenByTypeEx(SYMTAG.SymTagPointerType)
        DEBUG("PyDia.printPointerTypes", "len(children)", len(children))
        lines = []
        for symbol in children:
            pointerType = DiaPointerType(self, symbol)
            s = pointerType.declare()
            n = pointerType.sizeof()
            lines += [
                "",
                s,
                "sizeof({}) == {}".format(s,n)]
        self._printLines(*lines)

    def printArrayTypes(self):
        children = self.findChildrenByTypeEx(SYMTAG.SymTagArrayType)
        DEBUG("PyDia.printArrayTypes", "len(children)", len(children))
        lines = []
        for symbol in children:
            arrayType = DiaArrayType(self, symbol)
            s = arrayType.declare()
            n = arrayType.sizeof()
            lines += [
                "",
                s,
                "sizeof({}) == {}".format(s,n)]
        self._printLines(*lines)

    def _printChildrenByName_helper(self, symbol, context):
        printer = SymbolPrinter(self)
        DEBUG(context)
        if not symbol:
            DEBUG("", symbol)
            return
        symIndexId = symbol.symIndexId
        printer.debugSymbol(symbol)
        typeSymbol = symbol.type
        if typeSymbol:
            DEBUG(context + ".type")
            printer.debugSymbol(typeSymbol)
        subchildren = self.findChildrenEx(symbol)
        DEBUG(context + ".subchildren", "len(subchildren)={}".format(len(subchildren)))
        for subchild in subchildren:
            DEBUG(context + ".subchild")
            printer.debugSymbol(subchild)
            #self._printChildrenByName_helper(subchild, context + ".subchild")
        del printer
        
    def printChildrenByName(self, name):
        children = self.findChildrenByNameEx(name)
        DEBUG("PyDia.printChildrenByName", "len(children)", len(children))
        lines = []
        for symbol in children:
            self._printChildrenByName_helper(symbol, "")
        self._printLines(*lines)
        

    def printEnums(self, skipNested=False):
        children = self.findChildrenByTypeEx(SYMTAG.SymTagEnum)
        DEBUG("PyDia.printEnums", "skipNested={}".format(skipNested), "len(children)={}".format(len(children)))
        lines = []
        skipped = 0
        for symbol in children:
            if skipNested and symbol.nested:
                skipped += 1
                continue
            lines.append("")
            lines += EnumPrinter(self).defineLines(symbol)
        self._printLines(*lines)
        if skipped > 0:
            DEBUG("PyDia.printEnums", "skipped={}".format(skipped), "count={}".format(len(children)-skipped))

    def printBaseTypes(self):
        children = self.findChildrenByTypeEx(self.msdia.SymTagBaseType)
        DEBUG("PyDia.printBaseTypes", "len(children)", len(children))
        lines = []
        for symbol in children:
            s = TypePrinter(self).declare(symbol)
            n = symbol.length
            lines.append("")
            lines.append(s)
            lines.append("sizeof({}) == {}".format(s,n))
        self._printLines(*lines)

    def printSymTagCount(self, findByType):
        symbol = self.globalScope
        symTagName = {}
        symTagCount = {}
        for name in SYMTAG.__dict__.keys():
            if name.startswith("SymTag"):
                symTag = getattr(SYMTAG, name)
                symTagName[symTag] = name
                symTagCount[symTag] = 0
        if findByType:
            for symTag in symTagName.keys():
                symTagCount[symTag] = len(self.findChildrenByTypeEx(symTag, symbol))
        else:
            children = self.findChildrenEx(symbol)
            symTagCount[SYMTAG.SymTagNull] = len(children)
            for child in self.findChildrenEx(symbol):
                symTagCount[child.symTag] += 1
        DEBUG("PyDia.printSymTagCount", "findByType = {}".format(findByType))
        for symTag in symTagCount.keys():
            if symTagCount[symTag] != 0:
                DEBUG("PyDia.printSymTagCount", "{:<22} {:>2} : {:>6}".format(symTagName[symTag], symTag, symTagCount[symTag]))

    def printExe(self):
        SymbolPrinter(self).debugSymbol(self.globalScope)
        DEBUG("PyDia.printExe", " ".join(SymbolPrinter(self).metadata(self.globalScope)))

    def _print(self,*args):
        print ''.join(self.prefix) + ' '.join([str(arg) for arg in args]) + '\r\n',

    def _printLines(self,*lines):
        prefix = ''.join(self.prefix)
        data = []
        for line in lines:
            data += [prefix, line, '\r\n']
        print ''.join(data),


if __name__ == "__main__":
    t = time.clock()
    print "----- BEGIN -----\r\n",
    #pydia = PyDia("../highpriest-2008-11-05/HighPriest.exe")
    #pydia = PyDia("../client-twro-2004-03-09aSakexe/Sakexe_ep6.pdb")
    pydia = PyDia("../inter-cro-2009-10-15/InterServer.exe")
    #pydia = PyDia("../zone-cro-2009-07-03/ZoneProcess.exe")
    #pydia = PyDia("../zone-cro-2009-09-21/ZoneProcess.exe")
    #pydia = PyDia("D:/SHARE/-teste-/vc6/teste.exe")
    #pydia = PyDia("D:/SHARE/-teste-/vc9/teste.exe")
    try:
        #pydia.printExe()
        #pydia.printSymTagCount(True)#find by type
        #pydia.printSymTagCount(False)#find any (VERY SLOW!!! finds more symbol types)
        #pydia.printBaseTypes()
        #pydia.printEnums(True)#skip nested
        #pydia.printEnums(False)#all
        # TODO
        #pydia.printChildrenByName("CODBC")
        #pydia.printArrayTypes()
        #pydia.printPointerTypes()
        #pydia.printUDTs()
        #pydia.printUDT("PACKET_ZI_CHAT_PARTY")
        pydia.printUDT2("CNpc")
        #pydia.printVtable("CPc")
        #pydia.printUDTsByLength(46)
        #pydia.printFunctionTypes()
        # TODO
        #pydia.printDatas()
        #pydia.printSession()
    finally:
        del pydia
    print "----- END -----\r\n",
    t = time.clock() - t
    print "{}\r\n".format(t),
