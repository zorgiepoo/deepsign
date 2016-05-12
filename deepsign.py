#!/usr/bin/env python
#
# This tool can be used to code sign a bundle recursively with your own signature, whether that be ad-hoc ("-"), self-signed, a developer ID, etc..
# It is intended for alterations to signed applications, which may be done to remove or bypass restrictions and simple validation checks performed at run-time
# This behaves almost like `codesign --deep -fs` except codesign's deep signing does not handle some edge cases due to strange or poorly structured bundles 
# Note just like with `codesign --deep -s`, using this tool for application development is not recommended; prefer Xcode instead.
#

import os, sys, subprocess, argparse

CURRENT_DIRECTORY_PATH = "."

#Most directories are from Table 3 of https://developer.apple.com/library/mac/technotes/tn2206/_index.html
#Library/QuickLook was missing from the documentation, but it's probably needed. Hopefully nothing else is missing, but you never know.
#These paths are searched deeply (with the exception of CURRENT_DIRECTORY_PATH), so there can be sub-directories in them that may be traversed
#You may wonder, if that's the case, if we should just supply "Library" instead of particular directories inside of Library -- and that would be a good question...
#The order is intentional: everything except the main executable and root-level items are done first to ensure nested code gets signed first
VALID_SIGNING_PATHS = ["Frameworks", "PlugIns", "XPCServices", "Helpers", "Library/QuickLook", "Library/Automator", "Library/Spotlight", "Library/LoginItems", "Library/LaunchServices", "MacOS", CURRENT_DIRECTORY_PATH]

def log_message(message, newline=True):
	sys.stderr.write(message)
	if newline: sys.stderr.write("\n")

def log_message_bytes(message):
	try:
		log_message(message.decode("utf-8"), newline=False)
	except UnicodeDecodeError:
		pass

def executable_candidate(path):
	# Ignore top level files such as Info.plist, PkgInfo, etc..
	# We do this by only looking at executable permission marked files
	# Which should be a valid approach; anything that is sign-able should be marked executable (and vise versa), even .dylib/.so libraries
	# Note: do not check for Mach-O binaries specifically; technically other types of files can be signed (via xattr) like executable marked scripts, even though it's bad practice
	return (not os.path.islink(path) and not os.path.isdir(path) and os.access(path, os.X_OK))

def bundle_candidate(path):
	# Does the directory have a file extension - could it be a bundle?
	# Don't check for "Versions" or "Contents" - poorly structured bundles could be missing both
	filename = os.path.basename(os.path.normpath(path))
	return (not os.path.islink(path) and os.path.isdir(path) and len(os.path.splitext(filename)[1][1:]) > 0)

def codesign_file(path, identity, verbose):
	if verbose:
		log_message("Signing %s" % (path))

	process = subprocess.Popen(["codesign", "-fs", identity, path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	output, error = process.communicate()
	if verbose and output is not None:
		log_message_bytes(output)
	if verbose and error is not None:
		log_message_bytes(error)
	if process.returncode != 0:
		if not verbose and error is not None:
			log_message_bytes(error)
		log_message("Error: Failed to codesign %s" % (path))
		sys.exit(1)

def codesign_files_in(directory_path, identity, verbose):
	bundles = []
	executables = []

	#Iterate through the relative valid locations where code can be placed and expected to be signed at
	for signing_directory in VALID_SIGNING_PATHS:
		signing_directory_filename = os.path.join(directory_path, signing_directory)
		if os.path.exists(signing_directory_filename):
			for filename in os.listdir(signing_directory_filename):
				filepath = os.path.join(signing_directory_filename, filename)
				if bundle_candidate(filepath):
					bundles.append(filepath)
				elif executable_candidate(filepath):
					executables.append(filepath)
				elif signing_directory != CURRENT_DIRECTORY_PATH and os.path.isdir(filepath):
					# Another directory we should try to recurse into
					# For example: Contents/PlugIns/moo/foo.plugin is OK.
					codesign_files_in(filepath, identity, verbose)

	#Make sure we sign bundles before we sign executables because top-level executables may require
	#the bundles sitting right next to it to be signed first
	for bundle in bundles:
		codesign_bundle(bundle, identity, verbose)
	for executable in executables:
		codesign_file(executable, identity, verbose)

def codesign_versions(versions_path, identity):
	# Most likely we're in a framework bundle, but we could be in 'Contents/Versions/' from an app bundle too (although that is bad practice)
	# Find and sign all the versions, not just the 'default' version (if one even exists)
	# i.e, do not assume there is a "Current" symbolic link available, because it doesn't have to exist
	for filename in os.listdir(versions_path):
		filepath = os.path.join(versions_path, filename)
		if not os.path.islink(filepath):
			codesign_files_in(filepath, identity, verbose)

def codesign_bundle(bundle_path, identity, verbose):
	contents_path = os.path.join(bundle_path, "Contents")
	versions_path = os.path.join(bundle_path, "Versions")

	if os.path.exists(contents_path):
		# A normal bundle (.app, .xpc, plug-in, etc)

		# See if there's any 'Versions' to deal with first
		# Eg: Chrome includes a 'Versions' directory inside 'Contents'
		# Even though it is bad practice, standard codesign validation will pick it up.
		inner_versions_path = os.path.join(contents_path, "Versions")
		if os.path.exists(inner_versions_path):
			codesign_versions(inner_versions_path, identity)
		
		codesign_files_in(contents_path, identity, verbose)
	elif os.path.exists(versions_path):
		# A framework bundle
		codesign_versions(versions_path, identity)
	else:
		# A "bad" bundle that doesn't include a Versions or Contents directory, but is checked by standard codesign validation
		# Eg: Chrome includes a frameworks bundle that does this
		codesign_files_in(bundle_path, identity, verbose)
	
	# Don't forget to sign the bundle, which from my testing may be needed
	codesign_file(bundle_path, identity, verbose)

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Create code signatures for bundles recursively.")
	parser.add_argument("--verbose", "-v", help="Enable verbosity", action='store_true')
	parser.add_argument("signing_identity", help="Identity used when signing code. Same as in codesign(1)")
	parser.add_argument("bundle_path", help="Path to the bundle to sign recursively")

	args = parser.parse_args()
	
	verbose = args.verbose
	signing_identity = args.signing_identity
	sign_path = args.bundle_path

	if not os.path.exists(sign_path):
		log_message("Error: %s does not exist" % (sign_path))
		sys.exit(1)

	if executable_candidate(sign_path):
		codesign_file(sign_path, signing_identity, verbose)
	elif bundle_candidate(sign_path):
		codesign_bundle(sign_path, signing_identity, verbose)
	else:
		log_message("Error: Path provided is not suitable for being signed: %s" % (sign_path))
		sys.exit(1)
