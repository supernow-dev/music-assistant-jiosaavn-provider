# Unofficial JioSaavn Provider For Music Assistant
![License: MIT](https://img.shields.io/github/license/supernow-dev/music-assistant-jiosaavn-provider)
![GitHub release (latest by date)](https://img.shields.io/github/v/release/supernow-dev/music-assistant-jiosaavn-provider)


An unofficial music provider implementation to integrate JioSaavn unofficial API with Music Assistant. The source for 
unofficial API can be found [here](https://github.com/sumitkolhe/jiosaavn-api).

### Available Features
It supports all APIs of the unofficial JioSaavn API, i.e.
* Song search
* Album search
* Artist search
* Playlist search
* Recommended songs for the current songs
* Music Assistant "Don't stop the music!" and radio

**Prerequisite**: An instance of unofficial JioSaavn API is required either hosted locally or in cloud.

### Running it from a pre-built Docker image
> docker run -d --name music-assistant-jiosaavn --network host --cap-add=DAC_READ_SEARCH --cap-add=SYS_ADMIN --security-opt apparmor:unconfirmed -v `<host-data-folder>`:/data  supernow/music-assistant-jiosaavn:0.1.0

<sub>Replace `<host-data-folder>` with a folder from host.</sub>

### Building from source
1. Clone the [Music Assistant server](https://github.com/music-assistant/server) repository. (tested with release 2.6.3)
2. Create a folder inside the path -
    > music_assistant/providers/jiosaavn/
3. Clone this repo inside the newly created folder.
4. Follow the steps from Music Assistant repository to build it locally in the root folder.
    > uv build
    >
    > docker build -t supernow/music-assistant-jiosaavn:0.1.0 .
   > 
5. Run the following command to start the container. (optionally create a docker-compose file with the following configuration)
    > docker run -d --name music-assistant-jiosaavn --network host --cap-add=DAC_READ_SEARCH --cap-add=SYS_ADMIN --security-opt apparmor:unconfirmed -v `<host-data-folder>`:/data  supernow/music-assistant-jiosaavn:0.1.0
    > 
    <sub>Replace `<host-data-folder>` with a folder from host.</sub>
    

### Usage
1. Open Music Assistant web ui in browser and sign in/sign up.
2. Go to Settings -> Providers -> Add A New Provider -> Search for JioSaavn -> Add.
3. Configure the JioSaavn unofficial API base url in the configuration page and save.
4. Enjoy searching music and add them to your Music Assistant library.

### Acknowledgements
This project heavily relies on the following amazing projects. A big thank you to the developers for their hard work and contributions to the open-source community.
*   **[Music Assistant](https://github.com/music-assistant):** A music library manager for your offline and online music sources by [Open Home Foundation](https://www.openhomefoundation.org/).
*   **[JioSaavn API](https://github.com/sumitkolhe/jiosaavn-api):** An Unofficial API for downloading high-quality songs from JioSaavn .

### License

This project is licensed under the [MIT License](LICENSE) - see the [LICENSE](LICENSE) file for details.
