#!/usr/bin/python

# 	HypePowerPack.hype-export.py
#	Just some helpful additional actions for ...
#
#	v1.0.0 Logic, Queries, Expressions and Variables
#	v1.0.1 Fixed scope, HypeDocumentLoad in functions()
#	v1.0.2 limited to id, refactored python, IIFE
#
#
#	MIT License
#	Copyright (c) 2021 Max Ziebell
#

import argparse
import json
import sys
import os

# functions for conditions to inject in generated script
javascript_for_actions = """
(function () {
	/* @const */
	const _standalone = false;

	if("HYPE_eventListeners" in window === false) window.HYPE_eventListeners = Array();
	window.HYPE_eventListeners.push({"type":"HypeDocumentLoad", "callback":function (hypeDocument, element, event) {
		
		if (!_standalone) if (hypeDocument.documentName()!=="${hype_id}") return;

		hypeDocument.Conditional_Behavior = function (expression, isTrueBehavior, isFalseBehavior) {
			try {
				for(var key in hypeDocument.customData) eval('var '+ key +' = hypeDocument.customData[key];');
				var result = eval(expression);
			} catch (e){
				alert ("Condition Error: "+e);
				return;
			}
			if (result && isTrueBehavior){
				hypeDocument.triggerCustomBehaviorNamed(isTrueBehavior);
			} else if (!result && isFalseBehavior){
				hypeDocument.triggerCustomBehaviorNamed(isFalseBehavior);
			}
		}

		hypeDocument.Set_Variable = function (name, expression) {
			if (!hypeDocument.customData[name]) hypeDocument.customData[name] = null;
			try {
				for(var key in hypeDocument.customData) eval('var '+ key +' = hypeDocument.customData[key];');
				eval('hypeDocument.customData[name]='+expression);
			} catch (e){
				alert ("Variable Error: "+e);
			}
		}

		hypeDocument.Run_Function_by_Selector = function (fnc, selector) {
			if (!hypeDocument.functions()[fnc]) return;
			if (!selector) return;
			try {
				var sceneElm = document.getElementById(hypeDocument.currentSceneId());
				var elms = sceneElm.querySelectorAll(selector);
				elms.forEach(function(elm){
					hypeDocument.functions()[fnc].call(window, hypeDocument, elm, {type:'HypeQuery'});
				});
			} catch (e){
				alert ("Run Query Error: "+e);
			}
		}

		hypeDocument.Run_JavaScript_Expression = function (expression) {
			try {
				for(var key in hypeDocument.customData) eval('var '+ key +' = hypeDocument.customData[key];');
				eval(expression);
			} catch (e){
				alert ("Expression Error: "+e);
			}
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

	args, unknown = parser.parse_known_args()

	if args.get_options:		
		# add actions
		def extra_actions():
			return [
				{"label" : "Conditional Behavior", "function" : "HypePowerPack.Conditional_Behavior", "arguments":[{"label":"Expression", "type": "String"}, {"label":"Behavior true", "type": "String"}, {"label":"Behavior false", "type": "String"}]},
				{"label" : "Set Variable", "function" : "HypePowerPack.Set_Variable", "arguments":[{"label":"Variable", "type": "String"}, {"label":"Expression", "type": "String"}]},
				{"label" : "Run Function by Selector", "function" : "HypePowerPack.Run_Function_by_Selector", "arguments":[{"label":"Function", "type": "String"}, {"label":"Query Selector", "type": "String"}]},
				{"label" : "Run JavaScript Expression", "function" : "HypePowerPack.Run_JavaScript_Expression", "arguments":[{"label":"Expression", "type": "String"}]},
			]

		def save_options():
			return {
				"allows_export" : True,
				"allows_preview" : True,
			}
		
		options = {
			"extra_actions" : extra_actions(),
			"save_options" : save_options(),
			"min_hype_build_version" : "596",
			#"max_hype_build_version" : "670",
		}
	
		exit_with_result(options)

	elif args.modify_staging_path != None:
		import os
		import string
		import fnmatch
		import re

		# export info
		export_info_file = open(args.export_info_json_path)
		export_info = json.loads(export_info_file.read())
		export_info_file.close()
				
		# hype id	
		hype_id = os.path.basename (args.modify_staging_path)

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
					
		# read and prepare action helper
		global javascript_for_actions
		template = string.Template(javascript_for_actions)
		javascript_for_actions = template.substitute({"hype_id" : hype_id})
		
		def modify_generated_script(filepath):
			# read
			script = read_content(filepath)
			# replace relative with absolute calls in generated script
			script = script.replace('HypePowerPack', 'HYPE.documents[\\"'+hype_id+'\\"]')
			# prepand javascript for actions
			script = javascript_for_actions+script
			#save
			save_content(filepath, script)

		run_on_files(modify_generated_script, '*_hype_generated_script.js')


		import shutil
		shutil.rmtree(args.destination_path, ignore_errors=True)
		shutil.move(args.modify_staging_path, args.destination_path)

		exit_with_result(True)

# UTILITIES

# communicate info back to Hype
def exit_with_result(result):
	import sys
	print "===================="
	print json.dumps({"result" : result})
	sys.exit(0)


if __name__ == "__main__":
	main()
