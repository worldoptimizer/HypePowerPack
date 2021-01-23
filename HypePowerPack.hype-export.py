#!/usr/bin/python

# 	HypePowerPack.hype-export.py
#	Just some helpful additional actions for Tumult Hype
#
#	v1.0.0 Logic, Queries, Expressions and Variables
#	v1.0.1 Fixed scope, HypeDocumentLoad in functions()
#	v1.0.2 limited to id, refactored python, IIFE
#	v1.0.3 refactored JS, streamline API, replace Eval with new Function
#	v1.0.4 multi behavior, refactored JS , unpack functions, closure compiler
#
#
#	MIT License
#	Copyright (c) 2021 Max Ziebell
#

import argparse
import json
import sys
import distutils.util
import os

# functions for conditions to inject in generated script
javascript_for_hype_functions = """/** 
* Hype functions defined for HYPE.documents["${hype_id}"]
*/

if("HYPE_functions" in window === false) HYPE_functions = Object();
HYPE_functions["${hype_id}"] = Object();
"""

javascript_for_actions = """/** 
* Hype Power Pack v1.0.4 by Max Ziebell
*/

;(function () {
	/* @const */
	const _standalone = false;

	if("HYPE_eventListeners" in window === false) window.HYPE_eventListeners = Array();
	window.HYPE_eventListeners.push({"type":"HypeDocumentLoad", "callback":function (hypeDocument, element, event) {
		
		if (!_standalone) if (hypeDocument.documentName()!=="${hype_id}") return;

		var validNames = new RegExp('^[a-zA-Z_$][0-9a-zA-Z_$]*$');

		hypeDocument.conditionalBehavior = function (expression, isTrueBehavior, isFalseBehavior) {
			if (!expression || (!isTrueBehavior && !isFalseBehavior)) return;
			var result = this.runJavaScriptExpression(expression, 'Condition Error');
			if (result) {
				if (isTrueBehavior) hypeDocument.triggerCustomBehaviorNamedAll(isTrueBehavior);
			} else {
				if (isFalseBehavior) hypeDocument.triggerCustomBehaviorNamedAll(isFalseBehavior);
			}
		}

		hypeDocument.setVariable = function (variable, expression) {
			if (!variable || !expression) return;
			variable = variable.trim();
			if (!validNames.test(variable)) return;
			if (!hypeDocument.customData[variable]) hypeDocument.customData[variable] = null;
			hypeDocument.customData[variable] = this.runJavaScriptExpression(expression, 'Variable Error');
		}

		hypeDocument.runFunctionBySelector = function (fnc, selector) {
			if (!hypeDocument.functions()[fnc] || !selector) return;
			var sceneElm = document.getElementById(hypeDocument.currentSceneId());
			var elms = sceneElm.querySelectorAll(selector);
			elms.forEach(function(elm){
				hypeDocument.functions()[fnc].call(window, hypeDocument, elm, {type:'runFunctionBySelector'});
			});
		}

		hypeDocument.runJavaScriptExpression = function (expression, errorMsg, omitContext, omitError) {
			if (!expression) return;
			var context='';
			if (!omitContext) for(var variable in hypeDocument.customData) {
				if (validNames.test(variable)) 
					context+='var '+ variable +' = hypeDocument.customData["'+ variable +'"];';
			}
			try {
				return Function('hypeDocument', '"use strict";'+context+'return (' + expression + ')')(hypeDocument);
			} catch (e){
				alert ((errorMsg||'Expression Error')+(!omitError? ': '+e:''));
			}
		}

		hypeDocument.triggerCustomBehaviorNamedAll = function(behaviors){
			behaviors.split(',').forEach(function(behavior){
				hypeDocument.triggerCustomBehaviorNamed(behavior.trim());
			});
		}
		
		// Fire HypeDocumentLoad from hypeDocument.functions() if present
		if (hypeDocument.functions()['HypeDocumentLoad']) {
			hypeDocument.functions()['HypeDocumentLoad'](hypeDocument, element, event);
		}

		// Fallback for standalone code not needed when enabling exporter and inclusion in generated script
		if (_standalone) window.HypePowerPack = Object.values(HYPE.documents)[0];

		return true;
	}
	});

})();
"""

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument('--hype_version')
	parser.add_argument('--hype_build')

	parser.add_argument('--get_options', action='store_true')

	parser.add_argument('--modify_staging_path')
	parser.add_argument('--destination_path')
	parser.add_argument('--export_info_json_path')
	parser.add_argument('--is_preview', default="False")

	args, unknown = parser.parse_known_args()

	if args.get_options:		
		# add actions
		def extra_actions():
			return [
				{"label" : "Conditional Behavior", "function" : "HypePowerPack.conditionalBehavior", "arguments":[{"label":"Expression", "type": "String"}, {"label":"Behavior true", "type": "String"}, {"label":"Behavior false", "type": "String"}]},
				{"label" : "Set Variable", "function" : "HypePowerPack.setVariable", "arguments":[{"label":"Variable", "type": "String"}, {"label":"Expression", "type": "String"}]},
				{"label" : "Run Function by Selector", "function" : "HypePowerPack.runFunctionBySelector", "arguments":[{"label":"Function", "type": "String"}, {"label":"Selector", "type": "String"}]},
				{"label" : "Run JavaScript Expression", "function" : "HypePowerPack.runJavaScriptExpression", "arguments":[{"label":"Expression", "type": "String"}]},
			]

		def save_options():
			return {
				"allows_export" : True,
				"allows_preview" : True,
			}

		def document_arguments():
			return [
				setting.closure_compiler_on_export
			];
		
		options = {
			"document_arguments" : document_arguments(),
			"extra_actions" : extra_actions(),
			"save_options" : save_options(),
			"min_hype_build_version" : "596",
		}
	
		exit_with_result(options)

	elif args.modify_staging_path != None:

		import os
		import string
		import fnmatch
		import re
		import httplib, urllib

		# is preview
		is_preview = bool(distutils.util.strtobool(args.is_preview))

		# export info
		export_info_file = open(args.export_info_json_path)
		export_info = json.loads(export_info_file.read())
		export_info_file.close()
				
		# hype id	
		hype_id = os.path.basename (args.modify_staging_path)

		# read and prepare action helper
		global javascript_for_actions
		global javascript_for_hype_functions
		javascript_for_actions = javascript_for_actions.replace('${hype_id}', hype_id);
		javascript_for_hype_functions = javascript_for_hype_functions.replace('${hype_id}', hype_id);

		# file helper
		def read_content(filepath):
			with open(filepath, "r") as f:
				return f.read()

		def save_content(filepath, content):
			with open(filepath, "w") as f:
				f.write(content)

		def run_on_files(handler, filePattern):
			for path, dirs, files in os.walk(os.path.abspath(args.modify_staging_path)):
				for filename in fnmatch.filter(files, filePattern):
					filepath = os.path.join(path, filename)
					handler(filepath)

		# closure API
		def compile_with_closure(js_code):
			params = urllib.urlencode([
				('js_code', js_code),
				('compilation_level', 'SIMPLE_OPTIMIZATIONS'),
				('output_format', 'text'),
				('output_info', 'compiled_code'),
			])
			# send to API
			headers = { "Content-type": "application/x-www-form-urlencoded" }
			conn = httplib.HTTPSConnection('closure-compiler.appspot.com')
			conn.request('POST', '/compile', params, headers)
			response = conn.getresponse()
			compiled_code = response.read()
			conn.close()
			# return
			return compiled_code

		def has_setting(key):
			return key in export_info["document_arguments"]
		
		enabled_syntax = ['true', 'enabled', 'on']

		def enabled_setting(key):
			if key in export_info["document_arguments"]:
				return export_info["document_arguments"][key].lower() in enabled_syntax
			return False

		def modify_generated_script(filepath):
			# read
			script = read_content(filepath)
			# replace relative with absolute calls in generated script
			script = script.replace('exportScriptOid:"HypePowerPack.hype-export.py",', '')
			script = script.replace('HypePowerPack.', 'HYPE.documents[\\"'+hype_id+'\\"].')
			# hype function regex with Friedl's "unrolled loop"
			pattern = re.compile(r'name:"(.*?)",source:"([^"\\]*(?:\\.[^"\\]*)*)"')
			# append functions
			hype_functions = ''
			for m in re.finditer(pattern, script):
				new_name = 'HYPE_functions[\\"'+hype_id+'\\"].'+m.group(1)
				script = script.replace(m.group(2), new_name)
				new_name_decoded = new_name.decode('string_escape')
				function_decoded = m.group(2).decode('string_escape')
				hype_functions = hype_functions+"\n"+new_name_decoded+" = "+function_decoded+";\n"
			
			# add javascript for actions and hype functions
			script_additions = javascript_for_hype_functions+"\n"+hype_functions+"\n"+javascript_for_actions

			# use closure API on exports if enabled
			if not is_preview:
				if enabled_setting(setting.closure_compiler_on_export):
					script_additions = compile_with_closure(script_additions)
	
			# append script
			script = script_additions+"\n"+script;

			#save
			save_content(filepath, script)

		run_on_files(modify_generated_script, '*_hype_generated_script.js')


		import shutil
		shutil.rmtree(args.destination_path, ignore_errors=True)
		shutil.move(args.modify_staging_path, args.destination_path)

		exit_with_result(True)

# UTILITIES
class setting:
	closure_compiler_on_export = "Closure compiler on export"

# communicate info back to Hype
def exit_with_result(result):
	import sys
	print "===================="
	print json.dumps({"result" : result})
	sys.exit(0)


if __name__ == "__main__":
	main()
