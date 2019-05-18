from __future__ import print_function

import errno
import os
import sys
import traceback

from rospkg import RosPack
import genmsg
import genmsg.msgs
import genmsg.msg_loader
import genmsg.gentools

from genmsg import InvalidMsgSpec, MsgContext, MsgSpec, MsgGenerationException
from genmsg.base import log

from rdflib import Namespace, Literal, Graph
from rdflib.namespace import RDF, RDFS, OWL, XSD, NamespaceManager

DUL = Namespace("http://www.ontologydesignpatterns.org/ont/dul/DUL.owl#")
ROS = Namespace("http://www.ros.org/ont/ROS.owl#")
# FIXME: should not be used here
EASE_WF = Namespace("http://www.ease-crc.org/ont/EASE-WF.owl#")

SERIALIZE_FORMAT = 'xml'

def compute_resource_name(filename, ext):
    """
    Convert resource filename to ROS resource name
    :param filename str: path to .msg/.srv file
    :returns str: name of ROS resource
    """
    return os.path.basename(filename)[:-len(ext)]

def compute_outfile_name(outdir, infile_name, ext):
    """
    :param outdir str: path to directory that files are generated to
    :returns str: output file path based on input file name and output directory
    """
    # Use leading _ so that module name does not collide with message name. It also
    # makes it more clear that the .py file should not be imported directly
    return os.path.join(outdir, compute_resource_name(infile_name, ext)+".owl")

class GeneratorContex(object):
    def __init__(self, msg_context, spec, search_path):
        self.msg_context = msg_context
        self.spec = spec
        self.search_path = search_path
        self.name = spec.short_name
        self.pkg = spec.package
        self.md5 = genmsg.compute_md5(msg_context, spec)

class MsgGeneratorContex(GeneratorContex):
    def __init__(self, msg_context, spec, search_path):
        super(MsgGeneratorContex, self).__init__(msg_context, spec, search_path)
        self.ns = Namespace("http://www.ros.org/msg/%s.owl#"%(self.pkg))
        self.node_name = self.name
        self.msg_node = self.ns[self.node_name]

class ResGeneratorContex(MsgGeneratorContex):
    def __init__(self, srv_ctx):
        super(ResGeneratorContex, self).__init__(srv_ctx.msg_context,
                                                 srv_ctx.spec.response,
                                                 srv_ctx.search_path)
        self.msg_node = srv_ctx.res_node
        self.node_name = "%sResponse"%(srv_ctx.name)

class ReqGeneratorContex(MsgGeneratorContex):
    def __init__(self, srv_ctx):
        super(ReqGeneratorContex, self).__init__(srv_ctx.msg_context,
                                                 srv_ctx.spec.request,
                                                 srv_ctx.search_path)
        self.msg_node = srv_ctx.req_node
        self.node_name = "%sRequest"%(srv_ctx.name)

class SrvGeneratorContex(GeneratorContex):
    def __init__(self, msg_context, spec, search_path):
        super(SrvGeneratorContex, self).__init__(msg_context, spec, search_path)
        self.ns = Namespace("http://www.ros.org/srv/%s.owl#"%(self.pkg))
        self.node_name = self.name
        self.srv_node = self.ns[self.node_name]
        self.req_node = self.ns["%sReqest"%(self.node_name)]
        self.res_node = self.ns["%sResponse"%(self.node_name)]

class Generator(object):
    def __init__(self, what, ext, spec_loader_fn):
        self.what = what
        self.ext = ext
        self.spec_loader_fn = spec_loader_fn
        ##
        self.create_graph()
    
    def create_graph(self):
        self.rdf_graph = Graph()
        namespace_manager = NamespaceManager(self.rdf_graph)
        namespace_manager.bind('ros', ROS, override=False)
        namespace_manager.bind('dul', DUL, override=False)
        namespace_manager.bind('owl', OWL, override=False)
        namespace_manager.bind('rdf', RDF, override=False)
        namespace_manager.bind('wf', EASE_WF, override=False)
    
    def write_graph(self, outfile):
        self.rdf_graph.serialize(destination=outfile, format=SERIALIZE_FORMAT)
    
    def add_individual(self,node,rdf_type):
        self.add_triples(node, [(RDF.type,OWL.NamedIndividual),
                                (RDF.type,rdf_type)])
    
    def add_triples(self,s,triples):
        for (p,o) in triples:
            self.rdf_graph.add((s,p,o))
    
    def add_msg(self, msg_ctx):
        type_path = Literal("%s/%s"%(msg_ctx.pkg,msg_ctx.name), datatype=XSD.string)
        self.add_triples(msg_ctx.msg_node, [(ROS.hasTypePath,type_path),
                                            (ROS.hasMD5, Literal(msg_ctx.md5, datatype=XSD.string))])
        
        for field in msg_ctx.spec.parsed_fields():
            field_node = self.add_field(msg_ctx, field)
            self.add_triples(msg_ctx.msg_node, [(DUL.hasPart,field_node)])
    
    def add_field(self, msg_ctx, field):
        name = field.name
        msg_node_name = msg_ctx.node_name
        field_node = msg_ctx.ns["%s_%s"%(msg_node_name,name)]
        
        if field.is_array:
            self.add_individual(field_node, ROS.ArraySlot)
            if field.is_builtin:
                part = ROS[field.base_type]
            else:
                msg_pkg, msg_name = field.base_type.split('/')
                msg_ns = Namespace("http://www.ros.org/msg/%s.owl#"%(msg_pkg))
                part = msg_ns[msg_name]
        
        elif field.is_builtin:
            self.add_individual(field_node, ROS.PrimitiveSlot)
            part = ROS[field.base_type]
        
        else: # message type
            self.add_individual(field_node, ROS.MessageSlot)
            msg_pkg, msg_name = field.base_type.split('/')
            msg_ns = Namespace("http://www.ros.org/msg/%s.owl#"%(msg_pkg))
            part = msg_ns[msg_name]
        
        type_path = Literal("%s"%(name), datatype=XSD.string)
        self.add_triples(field_node, [(ROS.hasSlotName,type_path),(DUL.hasPart,part)])
        return field_node

    def generate(self, msg_context, full_type, f, outdir, search_path):
        try:
            # you can't just check first... race condition
            os.makedirs(outdir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
        spec = self.spec_loader_fn(msg_context, f, full_type)
        outfile = compute_outfile_name(outdir, os.path.basename(f), self.ext)
        self.generator_fn(msg_context, spec, search_path)
        self.write_graph(outfile)
        return outfile

    def generate_messages(self, package, package_files, outdir, search_path):
        """
        :returns: return code, ``int``
        """
        if not genmsg.is_legal_resource_base_name(package):
            raise MsgGenerationException("\nERROR: package name '%s' is illegal and cannot be used in message generation.\nPlease see http://ros.org/wiki/Names"%(package))
        
        rospack = RosPack()
        pkg_search_path = os.path.join(rospack.get_path(package), 'msg')
        
        # package/src/package/msg for messages, packages/src/package/srv for services
        msg_context = MsgContext.create_default()
        retcode = 0
        for f in package_files:
            try:
                f = os.path.abspath(f)
                infile_name = os.path.basename(f)
                search_path[package] = [pkg_search_path, os.path.dirname(f)]
                full_type = genmsg.gentools.compute_full_type_name(package, infile_name);
                outfile = self.generate(msg_context, full_type, f, outdir, search_path) #actual generation
                self.create_graph()
            except Exception as e:
                if not isinstance(e, MsgGenerationException) and not isinstance(e, genmsg.msgs.InvalidMsgSpec):
                    traceback.print_exc()
                print("\nERROR: Unable to generate %s for package '%s': while processing '%s': %s\n"%(self.what, package, f, e), file=sys.stderr)
                retcode = 1 #flag error
        return retcode

class MsgGenerator(Generator):
    def __init__(self):
        super(MsgGenerator, self).__init__('messages', genmsg.EXT_MSG,
                                           genmsg.msg_loader.load_msg_from_file)
    
    def generator_fn(self, msg_context, spec, search_path):
        try:
            genmsg.msg_loader.load_depends(msg_context, spec, search_path)
        except InvalidMsgSpec as e:
            raise MsgGenerationException("Cannot generate .msg for %s: %s"%(spec.full_name, str(e)))
        self.add_msg(MsgGeneratorContex(msg_context, spec, search_path))

class SrvGenerator(Generator):
    def __init__(self):
        super(SrvGenerator, self).__init__('services', genmsg.EXT_SRV,
                                           genmsg.msg_loader.load_srv_from_file)
    
    def generator_fn(self, msg_context, spec, search_path):
        genmsg.msg_loader.load_depends(msg_context, spec, search_path)
        ctx = SrvGeneratorContex(msg_context, spec, search_path)
        
        type_path = Literal("%s/%s"%(ctx.pkg,ctx.name), datatype=XSD.string)
        
        self.add_individual(ctx.srv_node,ROS.ServiceInterface)
        self.add_triples(ctx.srv_node,[
            (ROS.hasRequestType, ctx.req_node),
            (ROS.hasResponseType, ctx.res_node),
            (ROS.hasTypePath, type_path),
            (ROS.hasMD5, Literal(ctx.md5, datatype=XSD.string))])
    
        self.add_msg(ReqGeneratorContex(ctx))
        self.add_msg(ResGeneratorContex(ctx))
        
        tsk_node = ctx.ns["%s_Task"%(ctx.name)]
        self.add_individual(tsk_node,DUL.Task)
        
        exec_node = ctx.ns["%s_Execution"%(ctx.name)]
        self.add_individual(exec_node,ROS.ROSQueryingExecution)
        self.add_triples(exec_node, [(DUL.defines,tsk_node),
                                     (DUL.describes,ctx.srv_node)])
        
        params = []
        for field in ctx.spec.request.parsed_fields():
            field_node = ctx.ns["%sRequest"%(ctx.name)]
            params.append((ctx.ns["%s_Input_%s"%(ctx.name,field.name)],field_node,field))
        for field in ctx.spec.response.parsed_fields():
            field_node = ctx.ns["%sResponse"%(ctx.name)]
            params.append((ctx.ns["%s_Output_%s"%(ctx.name,field.name)],field_node,field))
        
        for param_node, field_node, field in params:
            self.add_individual(param_node,DUL.Parameter)
            self.add_triples(tsk_node, [(DUL.hasParameter,param_node)])
            
            binding_node = ctx.ns["%s_Binding_%s"%(ctx.name,field.name)]
            self.add_individual(binding_node,EASE_WF.RoleFillerBinding)
            self.add_triples(binding_node, [(EASE_WF.hasBindingFiller,field_node),
                                            (EASE_WF.hasBindingRole,param_node)])
            self.add_triples(exec_node, [(EASE_WF.hasBinding,binding_node)])

