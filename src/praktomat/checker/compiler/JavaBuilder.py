# -*- coding: utf-8 -*-

"""
A Java bytecode compiler for construction.
"""

import os
import string
from praktomat.checker.compiler.Builder import Builder
from django.conf import settings


class JavaBuilder(Builder):
	"""	 A Java bytecode compiler for construction. """

	# Initialization sets own attributes to default values.
	_compiler	= settings.JAVA_BINARY
	_language	= "Java"

	def exec_file(self, tmpdir, program_name):
		""" File of the generated executable
	
		To support java packages it is neccessary to recursively search for the .class file beneath the temporary directory.
		@param self reference to this object.
		@param tmpdir the temporary directory for this solution check.
		@param program_name the name of the executable java class (the class containing public static void main(String[] args) without package information.
		@return string containing the executable java .class file or None if no such file could be generated by the java compiler. """

		# first test if file exists in tmpdir
		file = os.path.join(tmpdir, program_name + ".class")
		if os.path.isfile(file):
			return file
		else:
			# if not, then recursively search for it in the subdirectories.
			for file in os.listdir(tmpdir):
				subdir = os.path.join(tmpdir, file)
				if os.path.isdir(subdir):
					file = self.exec_file(subdir, program_name)
					if None != file:
						return file
		return None

	def make_class_from_exec_path(self, exec_file, base_dir):
		""" Create a java classname from its file path beneath a base directory.

		In detail: first chop off a prefix of the size of the base directory and the ".class" suffix. Within the rest replace the directory separators with periods.
		@param self the class object itself.
		@param exec_file the path top the java class file.
		@param base_dir the base directory.
		@return string containing the class. """
		assert base_dir == exec_file[:len(base_dir)]
		chopped = exec_file[len(base_dir):len(exec_file)-len(".class")]
		(head, result) = os.path.split(chopped)
		while head != "/":
			chopped = string.join((head, result), ".")
			(head, result) = os.path.split(chopped)

		return result
	
	
	def run(self, env):
		""" run JavaBuilder """
		# run bilder of upperclass
		result = Builder.run(self, env)

		# check if 'executable' exists
		exec_file = self.exec_file(env.tmpdir(), env.program())
		passed = result.passed and (None != exec_file)
		result.set_passed(passed)
		
		if result.passed:
			# Reset the programname: it could be neccessary to add java
			# package information.
			env.set_program(self.make_class_from_exec_path(exec_file, env.tmpdir()))

		else:
			# Add a hint if the program did not compile
			new_log = result.log + u""" Es wurde kein ausführbares Programm erzeugt. Dies kann verschiedene Ursachen haben:

			1. Vermutlich ist das eingereichte Programm fehlerhaft und konnte nicht übersetzt werden. Korrigieren Sie die gemeldeten Fehler und reichen Sie erneut ein.
				
			2. Sie haben ihre Dateien in der falschen Reihenfolge angegeben. Als erste Datei muss der Quelltext mit der Hauptklasse (Methode public static void main(String[] args)) angegeben werden. Die Hauptklasse muss genau so heiﬂen wie die Datei.
				
			3. Sie haben ein Archiv eingereicht, in dem die	 Dateien in der falschen Reihenfolge aufgezeichnet sind. Die erste Datei in einem Archiv muss der Quelltext mit der Hauptklasse sein.	
			"""
			new_log = string.replace(new_log,"\n","<br/>") 
			result.set_log(new_log)
			
		return result
		
		
		
		
	
from praktomat.checker.admin import CheckerInline
from django.forms import ModelForm

class CheckerForm(ModelForm):
	def __init__(self, **args):
		""" override default values for the model fields """
		super(ModelForm, self).__init__(**args)
		self.fields["_flags"].initial = ""
		self.fields["_output_flags"].initial = ""
		#self.fields["_libs"].initial = ""
		self.fields["_file_pattern"].initial = r"^[a-zA-Z0-9_/\\]*\.[jJ][aA][vV][aA]$"
	
class JavaBuilderInline(CheckerInline):
	model = JavaBuilder
	form = CheckerForm
	