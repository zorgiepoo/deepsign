# deepsign

This tool can be used to code sign a bundle recursively with your own signature, whether that be ad-hoc ("-"), self-signed, a developer ID, etc..

It is intended for making alterations to signed applications, which may be done to remove or bypass simple restrictions enforced at run-time. This tool is modeled after `codesign --deep -fs` except it's designed to handle more edge cases.

Note just like with `codesign --deep -s`, using this tool for application development is not recommended; prefer Xcode instead for that.
