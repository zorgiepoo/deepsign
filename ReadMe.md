# deepsign

This tool can be used to code sign a bundle recursively with your own signing identity, whether that be ad-hoc ("-"), self-signed, a Developer ID, etc..

It is intended for making modifications to signed applications, which may be done to remove or bypass restrictions enforced at run-time. This tool is modeled after `codesign --deep -fs` except that it's intended to handle more applications & edge cases. See the source code for more info.

Note just like with `codesign --deep -s`, using this tool for application development is not recommended; prefer Xcode instead.

## Example Cases

### Bit Slicer
I have downloaded [Bit Slicer](https://github.com/zorgiepoo/Bit-Slicer) and I want to make it operate as a background application:

```
> /usr/libexec/PlistBuddy -c "Add :LSUIElement string 1" Bit\ Slicer.app/Contents/Info.plist
```
When I launch it I notice that it doesn't show up in that pesky Dock anymore. Yay! But the application can no longer gain memory access to other running processes because we violated the code signature.

So to fix that, I re-sign the application with my Developer ID certificate:

```
> python deepsign.py "Developer ID" Bit\ Slicer.app
```

And voila! Note that this application has a strict signature requirement, meaning that using an ad-hoc signature here does no good.

### Maps

As a developer, I want to reverse engineer and debug Apple's Maps application.

```
> lldb /Applications/Maps.app
(lldb) target create "/Applications/Maps.app"
Current executable set to '/Applications/Maps.app' (x86_64).
(lldb) run
error: process exited with status -1 (cannot attach to process due to System Integrity Protection)
(lldb) 
```

Tough luck! We could reboot our Mac and disable System Integrity Protection, or if we are feeling extra lazy:

```
> cp -R /Applications/Maps.app ~/Desktop/
> python deepsign.py "-" ~/Desktop/Maps.app
> lldb ~/Desktop/Maps.app
(lldb) target create "/Users/msp/Desktop/Maps.app"
Current executable set to '/Users/msp/Desktop/Maps.app' (x86_64).
(lldb) run
Process 6113 launched: '/Users/msp/Desktop/Maps.app/Contents/MacOS/Maps' (x86_64)
```

And we are all good :). Note in this case I used an ad-hoc ("-") signature.

## Side Effects

Naturally changing an application's code signature may have some undesired effects. For one, if the signature of an application changes, OS X's Keychain may not recgonize the new signature and will ask to allow changes. Some applications could decide to bail due to additional checks they may enforce. Others could fail to cooperate with certain services like iCloud. Applications could possibly even operate in a different "namespace", and so on.

While code signatures are not intended to change from one application version to the next, there is always the possibility a developer could lose access or have their initial certificate compromised. But how the developer signs their application and how a user may re-sign it can also differ in some ways.

Live dangerously!
