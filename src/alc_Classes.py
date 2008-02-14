#
# $Id: alc_Classes.py 876 2007-12-15 22:15:11Z Paradox $
#
#    Copyright (C) 2005-2006  Alcugs pyprp Project Team
#    See the file AUTHORS for more info about the team
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#    Please see the file COPYING for the full license.
#    Please see the file DISCLAIMER for more details, before doing nothing.
#

try:
    import Blender
    try:
        from Blender import Mesh
        from Blender import Lamp
    except Exception, detail:
        print detail
except ImportError:
    pass

import md5, random, binascii, cStringIO, copy, Image, math, struct, StringIO, os, os.path, pickle
from alcurutypes import *
from alcdxtconv import *
from alchexdump import *
from alc_GeomClasses import *
from alc_Functions import *
from alcConvexHull import *
from alc_AbsClasses import *
from alc_VolumeIsect import *
from alc_AlcScript import *


import alcconfig, alchexdump
def stripIllegalChars(name):
    name=name.replace("*","_")
    name=name.replace("?","_")
    name=name.replace("\\","_")
    name=name.replace("/","_")
    name=name.replace("<","_")
    name=name.replace(">","_")
    name=name.replace(":","_")
    name=name.replace("\"","_")
    name=name.replace("|","_")
    name=name.replace("#","_")
    name=name.strip()
    return name
    
        
########
## Material and layer classes are in alc_MatClasses.py
#########

class plSpawnModifier(plMultiModifier):    
    def __init__(self,parent,name="unnamed",type=0x003D):
        plMultiModifier.__init__(self,parent,name,type)

    def _Find(page,name):
        return page.find(0x003D,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x003D,name,1)
    FindCreate = staticmethod(_FindCreate)

    def changePageRaw(self,sid,did,stype,dtype):
        plMultiModifier.changePageRaw(self,sid,did,stype,dtype)

    def read(self,stream):
        plMultiModifier.read(self,stream)

    def write(self,stream):
        plMultiModifier.write(self,stream)
    
    def import_obj(self,obj):
        obj.addProperty("type","swpoint")
        obj.layers = [2,]
        try:
            obj.setDrawMode(9)
        except:
            obj.setDrawMode(10)
        obj.setDrawType(2)    

    def _Export(page,obj,scnobj,name):
        #create the spawn modifier
        
        # Hmm, redundant safety.... probably having two 
        found=0
        for mod in scnobj.data.data2.vector:
            if mod.Key.object_type==0x3D: #SpawnModifier
                found=1
                break
        if not found:
            mod= plSpawnModifier.FindCreate(page,name)
            scnobj.data.addModifier(mod)

    Export = staticmethod(_Export)


class plViewFaceModifier(plSingleModifier):
    plVFFlags = \
    { \
        "kPivotFace"    :  0, \
        "kPivotFavorY"  :  1, \
        "kPivotY"       :  2, \
        "kPivotTumble"  :  3, \
        "kScale"        :  4, \
        "kFaceCam"      :  5, \
        "kFaceList"     :  6, \
        "kFacePlay"     :  7, \
        "kFaceObj"      :  8, \
        "kOffset"       :  9, \
        "kOffsetLocal"  : 10, \
        "kMaxBounds"    : 11  \
    }
    
    
    def __init__(self, parent, name="unnamed", type=0x0040):
        plSingleModifier.__init__(self, parent, name, type)
        self.fScale = Vertex()
        self.fOrigLocalToParent = hsMatrix44()
        self.fOrigParentToLocal = hsMatrix44()
        self.fOffset = Vertex()
        self.fMaxBounds = hsBounds3Ext()
        self.fFaceObj = UruObjectRef(self.getVersion()) 

    def _Find(page,name):
        return page.find(0x0040,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x0040,name,1)
    FindCreate = staticmethod(_FindCreate)

    def read(self, stream):
        plSingleModifier.read(self,stream)
        self.fScale.read(stream) 
        self.fOrigLocalToParent.read(stream)
        self.fOrigParentToLocal.read(stream)
        if(self.bitVector[plViewFaceModifier.plVFFlags["kFaceObj"]]):
            self.fFaceObj.read(stream)
        self.fOffset.read(stream)
        if(self.bitVector[plViewFaceModifier.plVFFlags["kMaxBounds"]]):
            self.fMaxBounds.read(stream)

    def write(self, stream):
        plSingleModifier.write(self,stream)
        self.fScale.write(stream)
        self.fOrigLocalToParent.write(stream)
        self.fOrigParentToLocal.write(stream)
        if(self.bitVector[plViewFaceModifier.plVFFlags["kFaceObj"]]):
            self.fFaceObj.write(stream)
        self.fOffset.write(stream)
        if(self.bitVector[plViewFaceModifier.plVFFlags["kMaxBounds"]]):
            self.fMaxBounds.write(stream) # only write this if needed


    def import_obj(self,obj):
        if(self.bitVector.Count > 0):
            obj.addProperty("sprite_flags",str(alcHex2Ascii(self.bitVector.Data[0],4)))
        else:
            obj.addProperty("sprite_flags",str(alcHex2Ascii(0x00,4)))
    
    def export_obj(self,obj):
        try:
            p=obj.getProperty("sprite_flags")
            BVData=alcAscii2Hex(str(p.getData()),4)
        except (AttributeError, RuntimeError):
            BVData = plViewFaceModifer.plVFFlags['kFaceCam']    | \
                     plViewFaceModifer.plVFFlags['kPivotY']     | \
                     plViewFaceModifer.plVFFlags['kPivotFavorY']
            pass
        self.bitVector.append(BVData)

        # get the matrices
        LocalToWorld=hsMatrix44()
        m=getMatrix(obj)
        m.transpose()
        LocalToWorld.set(m)
        self.fOrigLocalToParent = LocalToWorld

        WorldToLocal=hsMatrix44()
        m=getMatrix(obj)
        m.invert() 
        m.transpose()
        WorldToLocal.set(m)
        self.fOrigParentToLocal = WorldToLocal

        #now see if we need to add a bounding box
        if(self.bitVector[plViewFaceModifier.plVFFlags["kMaxBounds"]]):
            # build up a simple bounding box
            # get the object center
            vorigin = Vertex(0,0,0)
            vorigin.transform(LocalToWorld)
    
            # now we need to build up a bounding cube
            # get the objects bounding box
            verts=obj.getBoundBox()
    
            vmin = Vertex(verts[0][0],verts[0][1],verts[0][2])
            vmin.transform(WorldToLocal)
            vmax = Vertex(verts[6][0],verts[6][1],verts[6][2])
            vmax.transform(WorldToLocal)    
            # now determine the largest Delta[XYZ]
            dmax = 0
            dx = vmax.x-vmin.x
            if(dx > dmax):
                dmax = dx
            dy = vmax.y-vmin.y
            if(dy > dmax):
                dmax = dy
            dz = vmax.z-vmin.z
            if(dz > dmax):
                dmax = dz        
        
            # now determine if the box lies withing the origin on X,Y or Z
            if(vmin.x > 0 and vmax.x > 0):
                if(vmin.x > vmax.x):
                    offsetx = vmax.x
                else:
                    offsetx = vmin.x
            elif(vmin.x < 0 and vmax.x < 0):
                if(vmin.x < vmax.x):
                    offsetx = vmax.x
                else:
                    offsetx = vmin.x
            else:
                offsetx = 0
            
            if(vmin.y > 0 and vmax.y > 0):
                if(vmin.y > vmax.y):
                    offsety = vmax.y
                else:
                    offsety = vmin.y
            elif(vmin.y < 0 and vmax.y < 0):
                if(vmin.y < vmax.y):
                    offsety = vmax.y
                else:
                    offsety = vmin.y
            else:
                offsety = 0
            
            if(vmin.z > 0 and vmax.z > 0):
                if(vmin.z > vmax.z):
                    offsetz = vmax.z
                else:
                    offsetz = vmin.z
            elif(vmin.z < 0 and vmax.z < 0):
                if(vmin.z < vmax.z):
                    offsetz = vmax.z
                else:
                    offsetz = vmin.z
            else:
                offsetz = 0
            
            # now determine the approximate minimum distance to the object from the origin
            offsetxy = math.sqrt(math.pow(offsetx,2)+math.pow(offsety,2))
            roffset = math.sqrt(math.pow(offsetz,2)+math.pow(offsetxy,2))
        
            # take the roffset in account with making the bounding cube, and make it slightly 
            # larger than the bare minimum (1.1 times larger)
            
            rmax = ((dmax/2) + roffset) * 1.1
            
            # now build up the new bounding box:
            vmin = Vertex(vorigin.x - rmax,vorigin.y - rmax,vorigin.z - rmax)
            vmax = Vertex(vorigin.x + rmax,vorigin.y + rmax,vorigin.z + rmax)
    
            self.fMaxBounds.min = vmin
            self.fMaxBounds.max = vmax
            self.fMaxBounds.flags = 0x01 # a simple bounding box without any other data
        
        self.fScale = Vertex(1,1,1)
        self.fOffset = Vertex(0,0,0)

    def _Export(page,obj,scnobj,name):
        vfm = plViewFaceModifier.FindCreate(page,name + "_VFM")
        vfm.data.export_obj(obj)
        scnobj.data.addModifier(vfm)
    Export = staticmethod(_Export)

#list2
class plAGModifier(plSingleModifier):    
    def __init__(self,parent,name="unnamed",type=0x006C):
        plSingleModifier.__init__(self,parent,name,type)
        #format
        #U32 0
        #U32 0
        self.string = ""

    def _Find(page,name):
        return page.find(0x006C,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x006C,name,1)
    FindCreate = staticmethod(_FindCreate)

    def read(self,stream):
        plSingleModifier.read(self,stream)
        self.string = stream.ReadSafeString(self.getVersion())


    def write(self,stream):
        plSingleModifier.write(self,stream)
        stream.WriteSafeString(self.string,self.getVersion())



class plAGMasterMod(hsKeyedObject):    
    def __init__(self,parent,name="unnamed",type=0x006D):
        hsKeyedObject.__init__(self,parent,name,type)
        #format
        #U32 0
        self.str=str32(type=1)
        self.anims=[] #armature anims


    def _Find(page,name):
        return page.find(0x006D,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x006D,name,1)
    FindCreate = staticmethod(_FindCreate)

    def changePageRaw(self,sid,did,stype,dtype):
        hsKeyedObject.changePageRaw(self,sid,did,stype,dtype)
        for i in self.anims:
            i.changePageRaw(sid,did,stype,dtype)


    def read(self,stream):
        hsKeyedObject.read(self,stream)
        unk1, = struct.unpack("I",stream.read(4))
        ##myst5 unk1: 0x04
        if unk1 not in [0x00,]:
            raise "unk1 %08X" %unk1
        #On tpots always "", on old versions there is something here
        self.str.read(stream)
        if self.getVersion()==6:
            count1, = struct.unpack("H",stream.read(2))
        else:
            count1, = struct.unpack("I",stream.read(4))
        self.anims=[]
        for i in range(count1):
            ref = UruObjectRef(self.getVersion())
            ref.read(stream)
            #print ref, self.Key
            assert(ref.verify(self.Key))
            if ref.Key.object_type not in [0xF1,0xF2]:
                raise "armature anim %08X" %ref.Key.object_type
            self.anims.append(ref)


    def write(self,stream):
        hsKeyedObject.write(self,stream)
        stream.write(struct.pack("I",0))
        self.str.write(stream)
        stream.write(struct.pack("I",len(self.anims)))
        for ref in self.anims:
            ref.update(self.Key)
            ref.write(stream)


class plExcludeRegionModifier(plSingleModifier):
    Flags = \
    { \
        "kBlockCameras" : 0 \
    }
    
    def __init__(self,parent,name="unnamed",type=0x00A4):
        plSingleModifier.__init__(self,parent,name,type)

        self.fSafePoints = []
        self.fSeek = True
        self.fSeekTime = 10

    def _Find(page,name):
        return page.find(0x00A4,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x00A4,name,1)
    FindCreate = staticmethod(_FindCreate)

    def read(self,stream):
        plSingleModifier.read(self,stream)
        
        count = stream.Read32()
        for i in range(count):
            safepoint = UruObjectRef()
            safepoint.read(stream)
            self.fSafePoints.append(safepoint)

        self.fSeek = stream.ReadBool()
        self.fSeekTime = stream.ReadFloat()
    
    def write(self,stream):
        plSingleModifier.write(self,stream)
        
        stream.Write32(len(fSafePoints))
        for safepoint in self.fSafePoints:
            safepoint.write(stream)
            
        stream.WriteBool(self.fSeek)
        stream.WriteFloat(self.fSeekTime)

class plSoftVolume(plRegionBase):               #Type 0x0087 (Uru)
    def __init__(self,parent,name="unnamed",type=0x0087):
        plRegionBase.__init__(self,parent,name,type)
        #Format
        self.i70 = 0
        self.f74 = 1.0
        self.f78 = 0
    
    def _Find(page,name):
        return page.find(0x0087,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x0087,name,1)
    FindCreate = staticmethod(_FindCreate)

    def read(self,stream):
        plRegionBase.read(self,stream)
        self.i70 = stream.Read32()
        self.f74 = stream.ReadFloat()
        self.f78 = stream.ReadFloat()
    
    
    def write(self,stream):
        plRegionBase.write(self,stream)
        stream.Write32(self.i70)
        stream.WriteFloat(self.f74)
        stream.WriteFloat(self.f78)


class plSoftVolumeSimple(plSoftVolume):
    def __init__(self,parent,name="unnamed",type=0x0088):
        plSoftVolume.__init__(self,parent,name,type)
        #Format
        self.f80 = 0
        self.VI7C = None #plVolumeIsect instance


    def _Find(page,name):
        return page.find(0x0088,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x0088,name,1)
    FindCreate = staticmethod(_FindCreate)

    def read(self,stream,size):
        st=stream.tell()
        plSoftVolume.read(self,stream)
        self.f80 = stream.ReadFloat()
        vitype = stream.Read16()
        if (vitype != 0x0000):
            self.VI7C = PrpVolumeIsect(vitype,self.getVersion())
            if self.VI7C.data == None:
                size=size-(stream.tell()-st)
                self.rawdata=cStringIO.StringIO()
                self.rawdata.write(stream.read(size))
                self.rawdata.seek(0)
            else:
                self.VI7C.read(stream)

    def write(self,stream):
        plSoftVolume.write(self,stream)
        stream.WriteFloat(self.f80)
        if self.VI7C == None:
            stream.Write16(0x0000)
        else:
            stream.Write16(self.VI7C.vitype)
            self.VI7C.write(stream)

 
    def getPropertyString(self):
        return str(self.Key.name)


    def import_all(self):
        name = str(self.Key.name)
        if self.VI7C.data != None:
            self.VI7C.data.createObject(name,self.getPageNum())

    def export_object(self,obj):
        # Pass this info to a convect volume isect
        self.VI7C = PrpVolumeIsect(0x02F5,self.getVersion())
        self.VI7C.data.export_object(obj)



class plSoftVolumeComplex(plSoftVolume):
    def __init__(self,parent,name="unnamed",type=0x0089):
        plSoftVolume.__init__(self,parent,name,type)
        #Format
        self.vSV7C = hsTArray([0x88,0x8A,0x8B,0x8C],self.getVersion(),True)

    def _Find(page,name):
        return page.find(0x0089,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x0089,name,1)
    FindCreate = staticmethod(_FindCreate)

    def read(self,stream):
        plSoftVolume.read(self,stream)
        self.vSV7C.read(stream)

    def write(self,stream):
        plSoftVolume.write(self,stream)
        self.vSV7C.write(stream)

    def getPropertyString(self):
        count = self.vSV7C.size
        if count > 0:
            propertyString = self.getPropertySymbol()
            propertyString += "("
            for i in range(count):
                if i > 0:
                    propertyString += ","
                svRef = self.vSV7C[i]
                softVolume = self.getRoot().findref(svRef)
                if softVolume != None:
                    propertyString += softVolume.data.getPropertyString()
                else:
                    raise RuntimeError, "Could not find soft volume object %s" % str(svRef.Key.name)
            propertyString += ")"
            return propertyString
        return None


class plSoftVolumeUnion(plSoftVolumeComplex):
    def __init__(self,parent,name="unnamed",type=0x008A):
        plSoftVolumeComplex.__init__(self,parent,name,type)

    def _Find(page,name):
        return page.find(0x008A,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x008A,name,1)
    FindCreate = staticmethod(_FindCreate)

    def getPropertySymbol(self):
        return "U"


class plSoftVolumeIntersect(plSoftVolumeComplex):
    def __init__(self,parent,name="unnamed",type=0x008B):
        plSoftVolumeComplex.__init__(self,parent,name,type)

    def _Find(page,name):
        return page.find(0x008B,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x008B,name,1)
    FindCreate = staticmethod(_FindCreate)

    def getPropertySymbol(self):
        return "I"


class plSoftVolumeInvert(plSoftVolumeComplex):
    def __init__(self,parent,name="unnamed",type=0x008C):
        plSoftVolumeComplex.__init__(self,parent,name,type)

    def _Find(page,name):
        return page.find(0x008C,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x008C,name,1)
    FindCreate = staticmethod(_FindCreate)

    def getPropertySymbol(self):
        return "!"


class plMsgForwarder(hsKeyedObject):    
    def __init__(self,parent,name="unnamed",type=0x00A8):
        hsKeyedObject.__init__(self,parent,name,type)
        #format
        self.mods=[] #modifiers

    def _Find(page,name):
        return page.find(0x00A8,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x00A8,name,1)
    FindCreate = staticmethod(_FindCreate)


    def changePageRaw(self,sid,did,stype,dtype):
        hsKeyedObject.changePageRaw(self,sid,did,stype,dtype)
        for i in self.mods:
            i.changePageRaw(sid,did,stype,dtype)


    def read(self,stream):
        hsKeyedObject.read(self,stream)
        count1, = struct.unpack("I",stream.read(4))
        self.mods=[]
        for i in range(count1):
            ref = UruObjectRef(self.getVersion())
            ref.read(stream)
            ##assert(ref.verify(self.Key))
            if ref.Key.object_type not in [0x6D,]:
                raise "modifier %08X" %ref.Key.object_type
            self.mods.append(ref)


    def write(self,stream):
        hsKeyedObject.write(self,stream)
        stream.write(struct.pack("I",len(self.mods)))
        for ref in self.mods:
            ##ref.update(self.Key)
            ref.write(stream)


class plArmatureEffectsMgr(hsKeyedObject):
    Sounds = \
    { \
        "kFootDirt"             :  0, \
        "kFootPuddle"           :  1, \
        "kFootWater"            :  2, \
        "kFootTile"             :  3, \
        "kFootMetal"            :  4, \
        "kFootWoodBridge"       :  5, \
        "kFootRopeLadder"       :  6, \
        "kFootGrass"            :  7, \
        "kFootBrush"            :  8, \
        "kFootHardWood"         :  9, \
        "kFootRug"              : 10, \
        "kFootStone"            : 11, \
        "kFootMud"              : 12, \
        "kFootMetalLadder"      : 13, \
        "kFootWoodLadder"       : 14, \
        "kFootDeepWater"        : 15, \
        "kFootMaintainerGlass"  : 16, \
        "kFootMaintainerStone"  : 17, \
        "kFootSwimming"         : 18, \
        "kMaxSurface"           : 19, \
        "kFootNoSurface"        : 19  \
    }
    
    SurfaceStrings = \
    [ \
        "Dirt", \
        "Puddle", \
        "Water", \
        "Tile", \
        "Metal", \
        "WoodBridge", \
        "RopeLadder", \
        "Grass", \
        "Brush", \
        "HardWood", \
        "Rug", \
        "Stone", \
        "Mud", \
        "MetalLadder", \
        "WoodLadder", \
        "DeepWater", \
        "Maintainer(Glass)", \
        "Maintainer(Stone)", \
        "Swimming", \
        "(none)"  \
    ]

    def __init__(self,parent,name="unnamed",type=0x00CD):
        hsKeyedObject.__init__(self,parent,name,type)
        
        self.fEffects = []

    def _Find(page,name):
        return page.find(0x00CD,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x00CD,name,1)
    FindCreate = staticmethod(_FindCreate)

    
    def changePageRaw(self,sid,did,stype,dtype):
        hsKeyedObject.changePageRaw(self,sid,did,stype,dtype)
    
    def read(self,stream):
        hsKeyedObject.read(self,stream)
        
        count = stream.Read32()
        for i in range(count):
            ref = UruObjectRef(self.getVersion())
            ref.read(stream)
            self.fEffects.append(ref)
    
    def write(self,stream):
        hsKeyedObject.write(self,stream)
        
        stream.Write32(len(self.fEffects))
        for ref in self.fEffects:
            ref.write(stream)



class plHardRegionPlanes(plRegionBase):
    def __init__(self,parent,name="unnamed",type=0x0111):
        plRegionBase.__init__(self,parent,name,type)
        self.vM70 = [] #hsMatrix34
    
    def _Find(page,name):
        return page.find(0x0111,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x0111,name,1)
    FindCreate = staticmethod(_FindCreate)

    def read(self,stream):
        plRegionBase.read(self,stream)
        count = stream.Read32()
        for i in range(count):
            self.vM70[i] = hsMatrix34()
            self.vM70.read(stream)
    
    def write(self,stream):
        plRegionBase.write(self,stream)
        count = len(self.vM70)
        stream.Write32(count)
        for i in range(count):
            self.vM70.write(stream)


class plHardRegionComplex(plRegionBase):
    def __init__(self,parent,name="unnamed",type=0x0112):
        plRegionBase.__init__(self,parent,name,type)
        self.vHR70 = hsTArray([],self.getVersion())
    
    def _Find(page,name):
        return page.find(0x0112,name,0)
    Find = staticmethod(_Find)

    def _FindCreate(page,name):
        return page.find(0x0112,name,1)
    FindCreate = staticmethod(_FindCreate)

    def read(self,stream):
        plRegionBase.read(self,stream)
        self.vHR70.read(self,stream)
    
    def write(self,stream):
        plRegionBase.write(self,stream)
        self.vHR70.write(stream)
    
    def changePageRaw(self,sid,did,stype,dtype):
        plRegionBase.changePageRaw(self,sid,did,stype,dtype)
        self.vHR70.changePageRaw(sid,did,stype,dtype)
        
class plVisRegion(plObjInterface):
    Flags = \
    { \
        "kRefRegion" : 0, \
        "kRefVisMgr" : 1  \
    }
    
    def __init__(self,parent,name="unnamed",type=0x0116):
        plObjInterface.__init__(self,parent,name,type)
        self.fRegion = UruObjectRef(self.getVersion())
        self.fMgr = UruObjectRef(self.getVersion())
    
    def _Find(page,name):
        return page.find(0x0116,name,0)
    Find = staticmethod(_Find)
    
    def _FindCreate(page,name):
        return page.find(0x0116,name,1)
    FindCreate = staticmethod(_FindCreate)
    
    def changePageRaw(self,sid,did,stype,dtype):
        plObjInterface.changePageRaw(self,sid,did,stype,dtype)
        self.fRegion.changePageRaw(sid,did,stype,dtype)
        self.fMgr.changePageRaw(sid,dad,stype,dtype)
    
    def read(self,stream):
        plObjInterface.read(self,stream)
        self.fRegion.read(stream)
        self.fMgr.read(stream)
    
    def write(self,stream):
        plObjInterface.write(self,stream)
        self.fRegion.write(stream)
        self.fMgr.write(stream)
