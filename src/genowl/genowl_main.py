from __future__ import print_function

from optparse import OptionParser

import os
import sys
import traceback
import genmsg
import genmsg.command_line
import errno

from genmsg import MsgGenerationException

from rospkg import RosPack
from genowl import generator

from rdflib import URIRef, Graph
from rdflib.namespace import RDF, OWL

def usage(progname):
    print("%(progname)s file(s)"%vars())

def parse_options(argv, progname):
    parser = OptionParser("%s file"%(progname))
    parser.add_option('-p', dest='package')
    parser.add_option('-o', dest='outdir')
    parser.add_option('-I', dest='includepath', action='append')
    return parser.parse_args(argv)

def genmodule(msg_files, srv_files, options):
    gen = generator.Generator('module', None, None)
    pkg = options.package
    outfile = os.path.join(options.outdir,'%s.owl'%(pkg))
    
    # add OWL.Ontology description
    ont_node = URIRef("http://www.ros.org/%s.owl"%(pkg))
    gen.add_triples(ont_node, [(RDF.type,OWL.Ontology)])
    
    # import ROS.owl
    rosowl_path = os.path.join(os.path.join(rospack.get_path('rosowl'), 'owl'), 'ROS.owl')
    gen.add_triples(ont_node, [(OWL.imports,URIRef(rosowl_path))])
    
    # import msg and srv OWL files
    for mode,files in [('msg',msg_files), ('srv',srv_files)]:
        outdir = os.path.join(options.outdir,mode)
        for f in files:
            f_name = f.split('/')[-1]
            owl_name = f_name.split('.')[0]+".owl"
            ont_file = os.path.join(outdir,owl_name).replace('/.private/','/')
            gen.add_triples(ont_node, [(OWL.imports,URIRef('file:'+ont_file))])
    
    gen.write_graph(outfile)
    
    return 0

def genpkg(argv, progname):
    options, args = parse_options(argv,progname)
    
    msg_files = []
    srv_files = []
    pkg_path = RosPack().get_path(options.package)
    retcode = 0
    
    for mode,files in [('msg',msg_files),('srv',srv_files)]:
        retcode_i = 0
        
        try:
            path = os.path.join(pkg_path,mode)
            for name in os.listdir(path):
                files.append(os.path.join(path,name))
            
            if files:
                args = files + [
                    '-p', options.package,
                    '-o', os.path.join(options.outdir, mode),
                    '-I', '%s:%s'%(options.package,path)]
                if mode=='msg':
                    retcode_i = genmain_(args, progname, generator.MsgGenerator())
                else:
                    retcode_i = genmain_(args, progname, generator.SrvGenerator())
        
        except Exception as e:
            traceback.print_exc()
            print("ERROR: ",e)
            retcode_i = 3
        
        if retcode_i!=0:
            retcode = retcode_i
        
    if retcode!=0:
        sys.exit(retcode)
    elif msg_files or srv_files:
        retcode = genmodule(msg_files, srv_files, options)
        sys.exit(retcode)

def genmain(argv, progname, gen):
    sys.exit(genmain_(argv, progname, gen))

def genmain_(argv, progname, gen):
    rospack = RosPack()
    options, args = parse_options(argv,progname)
    try:
        if len(args) < 2:
           parser.error("please specify args")
        if not os.path.exists(options.outdir):
            # This script can be run multiple times in parallel. We
            # don't mind if the makedirs call fails because somebody
            # else snuck in and created the directory before us.
            try:
                os.makedirs(options.outdir)
            except OSError as e:
                if not os.path.exists(options.outdir):
                    raise
        
        search_path = genmsg.command_line.includepath_to_dict(options.includepath)
        search_path['std_msgs'] = []
        for d in rospack.get_depends_on(options.package):
            search_path[d] = [os.path.join(rospack.get_path(d), 'msg')]
        
        retcode = gen.generate_messages(options.package, args[1:], options.outdir, search_path)
    except genmsg.InvalidMsgSpec as e:
        print("ERROR: ", e, file=sys.stderr)
        retcode = 1
    except MsgGenerationException as e:
        print("ERROR: ", e, file=sys.stderr)
        retcode = 2
    except Exception as e:
        traceback.print_exc()
        print("ERROR: ",e)
        retcode = 3
    return (retcode or 0)
