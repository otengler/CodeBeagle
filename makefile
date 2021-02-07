InterfaceFiles = MainWindow.ui LeaveLastTabWidget.ui ProgressBar.ui SearchPage.ui SourceViewer.ui SettingsItem.ui SettingsDialog.ui CheckableItemsDialog.ui HelpViewerDialog.ui UserHintDialog.ui AboutDialog.ui MatchesOverview.ui
CompiledInterfaceFiles = $(patsubst %.ui,Ui_%.py, $(InterfaceFiles))

Resources = LeaveLastTabWidget.qrc MainWindow.qrc SearchPage.qrc SettingsDialog.qrc
CompiledResources = $(patsubst %.qrc,%_rc.py, $(Resources))

.PHONY : all buildResources copyResourceFiles dist clean

all: $(CompiledInterfaceFiles) buildResources 

buildResources: copyResourceFiles $(CompiledResources)

$(CompiledInterfaceFiles): Ui_%.py : %.ui 
	pyuic4 -o $@ $<

$(CompiledResources): %_rc.py : %.qrc
	pyrcc4 -o $@ -py3 $<
	
copyResourceFiles:
	cp -u resources/Crystal/* resources/

dist: all
	-mkdir build
	-mkdir build/CodeBeagle
	-mkdir build/CodeBeagle/config
	-mkdir build/CodeBeagle/scripts
	cp *.py build/CodeBeagle
	cp *.pyw build/CodeBeagle
	cp scripts/* build/CodeBeagle/scripts
	cp config/* build/CodeBeagle/config
	cp config.txt build/CodeBeagle
	cp help.html LICENSE readme.txt build/CodeBeagle
	python3 -c "import compileall; compileall.compile_dir('build')"
	chmod +x build/CodeBeagle/CodeBeagle.pyw
	chmod +x build/CodeBeagle/UpdateIndex.py

clean:
	-rm -f resources/*
	-rm -f $(CompiledInterfaceFiles) 
	-rm -f $(CompiledResources)
	-rm -rf build


