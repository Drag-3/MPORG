# ACRFingerprinterPlugin

## Description
This plugin serves as a FingerprinterPlugin that uses the paid ACRCloud Service in order to fingerprint and gather metadata on unknown music files.

## Install-Instructions

This plugin requires some non-python dependencies on windows. The Visual C++ Redistributable 2015 must be installed on the users' system. Specific Instructions are below.

*NIX users do not need to install the non-python dependencies.  
**NOTE**: The following is for Windows users only. *NIX users can skip this section.

### Windows Install Instructions
To install the c++ runtime you have two options: 
1. Install the Visual C++ Redistributable 2015 using winget:
    - If you have winget installed you can use winget as it is the easier option
    ```bash
        winget install Microsoft.VCRedist.2015+.x64
    ```
2. Install the Visual C++ Redistributable 2015 from the Microsoft [site](https://www.microsoft.com/en-us/download/details.aspx?id=48145). Remember to install the x64 version.

## Credentials Required
This plugin requires an ACRCloud API Key and Secret along with a valid host url.  
To acquire an ACRCloud API key and secret, register your application at the [ACRCloud](https://console.acrcloud.com/signup) site.  


**NOTE**: For the first 20,000 Requests ACRCloud is $3 per 1000 valid requests. After that it gradually decreases to $1.7 (2023-09)   
**NOTE**: When running this plugin for the first time you will be prompted to enter your API Key and Secret. This will be stored in the config file and will not be prompted for it again.

## Credits
This plugin was written by Drag-3.