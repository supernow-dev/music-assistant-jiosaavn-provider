"""JioSaavn Music Assistant Provider."""
from typing import List, Optional, Dict
from urllib.parse import quote

from music_assistant_models.enums import (
    ProviderFeature,
    StreamType,
    ContentType,
    ImageType,
    MediaType,
)
from music_assistant_models.errors import MediaNotFoundError
from music_assistant_models.media_items import (
    Album,
    Artist,
    MediaItemImage,
    Playlist,
    SearchResults,
    Track,
    ProviderMapping
)
from music_assistant_models.streamdetails import StreamDetails, AudioFormat
from music_assistant.models.music_provider import MusicProvider
from music_assistant_models.config_entries import ConfigEntry, ConfigEntryType


async def setup(mass, config_entry, config):
    """Entry point called by Music Assistant."""
    # Correct argument order: (mass, config_entry, config)
    return JioSaavnProvider(mass, config_entry, config)


class JioSaavnProvider(MusicProvider):
    """Provider for JioSaavn."""

    def __init__(self, mass, config_entry, config):
        """Initialize the provider."""
        super().__init__(mass, config_entry, config)
        # self._api_url = "http://192.168.16.226:3000"
        api_url = self.config.get_value("api_url")
        if not api_url:
            raise ValueError("api_url is not configured")
        self._api_url = api_url.rstrip("/")
        self.logger.info(f"JioSaavn provider initialized with API URL: {self._api_url}")

    @property
    def supported_features(self):
        """Supported provider features."""
        return {
            ProviderFeature.SEARCH,
            ProviderFeature.BROWSE,
            ProviderFeature.ARTIST_ALBUMS,
            ProviderFeature.ARTIST_TOPTRACKS,
            ProviderFeature.SIMILAR_TRACKS
        }

    # ---------------------------------------------------------
    # SEARCH
    # ---------------------------------------------------------

    async def search(self, search_query: str, media_types: List[MediaType], limit: int = 10) -> SearchResults:
        """Perform search on the API."""
        results = SearchResults()
        encoded = quote(search_query)

        # Tracks (Using the new endpoint: /api/search/songs)
        if MediaType.TRACK in media_types:
            # New endpoint: /api/search/songs?query=<query>&limit=<limit>
            data = await self._get_data(f"api/search/songs?query={encoded}&limit={limit}")
            # The structure for results (data.get("data", {}).get("results")) is consistent with the sample
            if data and "results" in data.get("data", {}):
                for item in data["data"]["results"]:
                    results.tracks.append(self._parse_track(item))

        # Albums (Assuming endpoint remains the same)
        if MediaType.ALBUM in media_types:
            data = await self._get_data(f"api/search/albums?query={encoded}")
            if data and "results" in data.get("data", {}):
                for item in data["data"]["results"]:
                    results.albums.append(self._parse_album(item))

        # Artists (Assuming endpoint remains the same)
        if MediaType.ARTIST in media_types:
            data = await self._get_data(f"api/search/artists?query={encoded}&limit={limit}")
            if data and "results" in data.get("data", {}):
                for item in data["data"]["results"]:
                    results.artists.append(self._parse_artist(item))

        if MediaType.PLAYLIST in media_types:
            data = await self._get_data(f"api/search/playlists?query={encoded}&limit={limit}")
            if data and "results" in data.get("data", {}):
                for item in data["data"]["results"]:
                    results.playlists.append(self._parse_playlist(item))

        return results

    # ---------------------------------------------------------
    # LOOKUPS
    # ---------------------------------------------------------

    async def get_track(self, track_id: str) -> Track:
        data = await self._get_data(f"api/songs/{track_id}")
        if not data or not data.get("data"):
            raise MediaNotFoundError(f"Track {track_id} not found")

        track_data = data["data"][0] if isinstance(data["data"], list) else data["data"]
        return self._parse_track(track_data)

    async def get_album(self, album_id: str) -> Album:
        data = await self._get_data(f"api/albums?id={album_id}")
        if not data or not data.get("data"):
            raise MediaNotFoundError(f"Album {album_id} not found")
        return self._parse_album(data["data"])

    async def get_artist(self, artist_id: str) -> Artist:
        data = await self._get_data(f"api/artists/{artist_id}")
        if not data or not data.get("data"):
            raise MediaNotFoundError(f"Artist {artist_id} not found")
        return self._parse_artist(data["data"])

    async def get_album_tracks(self, album_id: str) -> List[Track]:
        data = await self._get_data(f"api/albums?id={album_id}")
        if not data or not data.get("data") or "songs" not in data["data"]:
            return []
        return [self._parse_track(song) for song in data["data"]["songs"]]

    async def get_artist_albums(self, artist_id: str) -> List[Album]:
        data = await self._get_data(f"api/artists/{artist_id}/albums")
        if not data or not data.get("data") or "albums" not in data["data"]:
            return []
        return [self._parse_album(item) for item in data["data"]["albums"]]

    async def get_artist_toptracks(self, artist_id: str) -> List[Track]:
        data = await self._get_data(f"api/artists/{artist_id}/songs")
        if not data or not data.get("data") or "songs" not in data["data"]:
            return []
        return [self._parse_track(item) for item in data["data"]["songs"]]

    async def get_playlist(self, playlist_id: str) -> Playlist:
        data = await self._get_data(f"api/playlists?id={playlist_id}")
        if not data or not data.get("data"):
            raise MediaNotFoundError(f"Playlist {playlist_id} not found")
        return self._parse_playlist(data["data"])

    async def get_playlist_tracks(self, playlist_id: str, page: int = 0) -> list[Track]:
        data = await self._get_data(f"api/playlists?id={playlist_id}&page={page}")
        if not data or not data.get("data"):
            return []
        playlist_data = data["data"]
        songs = playlist_data.get("songs", [])
        if not songs:
            return []
        return [self._parse_track(song) for song in songs]

    async def get_similar_tracks(self, prov_track_id: str, limit: int = 20) -> list[Track]:
        """Get similar/suggested tracks for a given track.

        Uses the JioSaavn suggestions endpoint: /api/songs/{id}/suggestions
        """
        self.logger.info(f"Getting similar tracks for: {prov_track_id}")

        try:
            # Call suggestions endpoint
            data = await self._get_data(f"api/songs/{prov_track_id}/suggestions")

            if not data or not data.get("data"):
                self.logger.warning(f"No suggestions found for track {prov_track_id}")
                return []

            suggestions_data = data["data"]
            similar_tracks = []

            # Parse suggested tracks
            if isinstance(suggestions_data, list):
                for item in suggestions_data[:limit]:
                    try:
                        track = self._parse_track(item)
                        if track:
                            similar_tracks.append(track)
                    except Exception as e:
                        self.logger.debug(f"Failed to parse similar track: {e}")
                        continue
            else:
                # Handle single object response
                try:
                    track = self._parse_track(suggestions_data)
                    if track:
                        similar_tracks.append(track)
                except Exception as e:
                    self.logger.error(f"Failed to parse suggestion track: {e}")

            self.logger.info(f"Found {len(similar_tracks)} similar tracks for {prov_track_id}")
            return similar_tracks

        except Exception as e:
            self.logger.error(f"Failed to get similar tracks for {prov_track_id}: {e}")
            return []

    # ---------------------------------------------------------
    # STREAMING
    # ---------------------------------------------------------

    async def get_stream_details(self, item_id: str, provider_item_id: str) -> StreamDetails:
        """Get stream details for a track - using HTTP_DIRECT to let FFmpeg fetch the URL."""
        # Use the raw provider_item_id to query your API
        data = await self._get_data(f"api/songs/{item_id}")
        if not data or not data.get("data"):
            raise MediaNotFoundError(f"Track {item_id} not found")

        track_data = data["data"][0] if isinstance(data["data"], list) else data["data"]

        download_urls = track_data.get("downloadUrl", [])
        if not download_urls:
            raise MediaNotFoundError("No stream found")

        quality_order = ["320kbps", "160kbps", "96kbps", "48kbps"]

        chosen = None
        for q in quality_order:
            for d in download_urls:
                if d.get("quality") == q:
                    chosen = d.get("url")
                    break
            if chosen:
                break

        # Fallback to the last one in the list if preferred quality not found
        if not chosen and download_urls:
            chosen = download_urls[-1].get("url")

        if not chosen:
            raise MediaNotFoundError("No playable URL found in song data")

        # Create the AudioFormat object
        audio_format = AudioFormat(
            content_type=ContentType.MP4,
            sample_rate=44100,
            bit_depth=16,
            channels=2
        )

        # FIX: Use HTTP_DIRECT and set stream_type so FFmpeg fetches the URL directly
        return StreamDetails(
            provider=self.instance_id,
            item_id=item_id,
            media_type=MediaType.TRACK,
            path=chosen,
            audio_format=audio_format,
            stream_type=StreamType.HTTP,  # ← KEY FIX: Let FFmpeg handle the URL
            can_seek=True,  # ← JioSaavn supports seeking
        )

    # ---------------------------------------------------------
    # HTTP Helper
    # ---------------------------------------------------------

    async def _get_data(self, endpoint: str) -> Optional[dict]:
        url = f"{self._api_url}/{endpoint}"
        try:
            async with self.mass.http_session.get(url) as resp:
                if resp.status != 200:
                    self.logger.error(f"JioSaavn API error {resp.status}: {url}")
                    return None
                return await resp.json()
        except Exception:
            self.logger.exception("Failed calling JioSaavn API")
            return None

    # ---------------------------------------------------------
    # Parsing helpers
    # ---------------------------------------------------------

    def _parse_image(self, images: List[Dict]) -> Optional[MediaItemImage]:
        if not images:
            return None
        # Always try to pick the largest available image (last one in the list based on the sample)
        url = images[-1].get("url")
        if not url:
            return None

        # FIX: Add the required 'provider' argument
        return MediaItemImage(
            type=ImageType.THUMB,
            path=url,
            provider=self.instance_id
        )

    def _parse_track(self, data: Dict) -> Track:
        # Create the ProviderMapping for the Track
        prov_mapping = ProviderMapping(
            item_id=data.get("id"),
            provider_domain=self.domain,
            provider_instance=self.instance_id,
            url=data.get("url")
            # FIX: REMOVED 'name' argument
        )

        track = Track(
            item_id=data.get("id"),
            provider=self.instance_id,
            name=data.get("name", ""),
            # Pass the mapping object here
            provider_mappings=[prov_mapping],
        )
        # Duration is in seconds
        track.duration = int(data.get("duration", 0))

        # Album
        if "album" in data and isinstance(data["album"], dict):
            # The search result provides a simplified album object, which we can parse
            album_data = data["album"]
            album = Album(
                item_id=album_data.get("id"),
                provider=self.instance_id,
                name=album_data.get("name", ""),
                # Use a simplified mapping for the nested album object
                provider_mappings=[ProviderMapping(
                    item_id=album_data.get("id"),
                    provider_domain=self.domain,
                    provider_instance=self.instance_id,
                    url=album_data.get("url")
                )]
            )
            # We also get the year from the main track object if available
            if "year" in data:
                try:
                    album.year = int(data["year"])
                except:
                    pass
            track.album = album

        # Artists
        if "artists" in data and "primary" in data["artists"]:
            for a in data["artists"]["primary"]:
                track.artists.append(self._parse_artist(a))

        # Images
        img = self._parse_image(data.get("image", []))
        if img:
            track.metadata.images = [img]

        # Explicit content flag
        if data.get("explicitContent"):
            track.metadata.explicit = True

        return track

    def _parse_album(self, data: Dict) -> Album:
        # Create the ProviderMapping for the Album
        prov_mapping = ProviderMapping(
            item_id=data.get("id"),
            provider_domain=self.domain,
            provider_instance=self.instance_id,
            url=data.get("url")
            # FIX: REMOVED 'name' argument
        )

        album = Album(
            item_id=data.get("id"),
            provider=self.instance_id,
            name=data.get("name", ""),
            # Pass the mapping object here
            provider_mappings=[prov_mapping],
        )
        if "year" in data:
            try:
                album.year = int(data["year"])
            except:
                pass

        img = self._parse_image(data.get("image", []))
        if img:
            album.metadata.images = [img]

        # Artists from full album data or search result's artist object
        artists_data = data.get("artists", {})
        if "primary" in artists_data:
            for a in artists_data["primary"]:
                album.artists.append(self._parse_artist(a))

        return album

    def _parse_artist(self, data: Dict) -> Artist:
        # Create the ProviderMapping for the Artist
        prov_mapping = ProviderMapping(
            item_id=data.get("id"),
            provider_domain=self.domain,
            provider_instance=self.instance_id,
            url=data.get("url")
            # FIX: REMOVED 'name' argument
        )

        artist = Artist(
            item_id=data.get("id"),
            provider=self.instance_id,
            name=data.get("name", ""),
            # Pass the mapping object here
            provider_mappings=[prov_mapping],
        )
        img = self._parse_image(data.get("image", []))
        if img:
            artist.metadata.images = [img]
        return artist

    def _parse_playlist(self, data: Dict) -> Playlist:
        prov_mapping = ProviderMapping(
            item_id=data.get("id"),
            provider_domain=self.domain,
            provider_instance=self.instance_id,
            url=data.get("url")
        )

        playlist = Playlist(
            item_id=data.get("id"),
            provider=self.instance_id,
            name=data.get("name", ""),
            provider_mappings=[prov_mapping],
        )

        # Add description, image, owner
        if "description" in data:
            playlist.metadata.description = data["description"]

        img = self._parse_image(data.get("image", []))
        if img:
            playlist.metadata.images = [img]

        # Add curator/owner
        if "owner" in data:
            owner_data = data["owner"]
            if isinstance(owner_data, dict):
                owner_artist = Artist(...)
                playlist.metadata.curator = owner_artist

        return playlist


# async def get_config_entries(mass, instance_id, action=None, values=None):
#     """No configuration UI."""
#     return []

# This is a MODULE-LEVEL async function, not a class method!
async def get_config_entries(
        mass,
        instance_id: str,
        action: str | None = None,
        values: dict | None = None,
) -> list[ConfigEntry]:
    """Return the config entries for this provider."""
    return [
        ConfigEntry(
            key="api_url",
            type=ConfigEntryType.STRING,
            label="API Base URL",
            description="Base URL of the JioSaavn API (e.g. http://192.168.16.226:3000)",
            default_value="http://192.168.16.226:3000",
            required=True,
        ),
    ]
