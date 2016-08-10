# DCP-interval-finder

This program allows you to automatically discover the timestamp of the interval/intermission in a movie.

Just start it and select a Digital Cinema Package Composition PlayList (DCP CPL) file

```sh
$ python interval_finder.py
```
![Screenshot](img/screen.png?raw=true "Screenshot")

### Features:
  - XML file manual selection
  - XML file search by name or UUID
  - Reel List graphical representation with timestamps
  - Suggestion of the best timestamp for the interval
  - 100% Offline. No Internet access needed on your Theater Management System (TMS)

### Release Notes:
  - DCP-interval-finder does not rely on any online database: reels data is extracted from local XML file and the suggested timestamp is the starting point of the reel nearest to the middle time
  - You need to configure/select the local directory where your TMS stores DCP files after the ingest
  - This program requires Python Tkinter module
