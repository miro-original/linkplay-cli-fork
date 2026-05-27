import logging
import re
from http import HTTPStatus
from typing import Optional

import requests
from bs4 import BeautifulSoup

PLAYLIST_ID_IN_TRACK_SOURCE_REGEX = r'spotify:playlist:(?P<playlist_id>[a-zA-Z0-9]+)'
COLLECTION_TRACK_SOURCE_REGEX = r'spotify:user:(?P<user_id>[a-zA-Z0-9]+):collection(?::artist:(?P<artist_id>[a-zA-Z0-9]+))?'


def _get_playlist_owner(track_source: str) -> Optional[str]:
    match_result = re.match(PLAYLIST_ID_IN_TRACK_SOURCE_REGEX, track_source)
    if not match_result:
        logging.debug(f'TrackSource is not a Spotify playlist: {track_source}')
        return None
    playlist_id = match_result.group('playlist_id')

    try:
        playlist_response = requests.get(f'https://open.spotify.com/playlist/{playlist_id}')
    except requests.exceptions.RequestException as e:
        logging.debug(f'Spotify playlist request failed with the following exception: {e}')
        return None
    if playlist_response.status_code != HTTPStatus.OK:
        logging.debug(f'Spotify playlist request failed with status code {playlist_response.status_code}')
        return None

    soup = BeautifulSoup(playlist_response.text, 'html.parser')
    og_description = soup.find('meta', property='og:description')
    og_description_content = og_description.get('content') if og_description else None
    if not isinstance(og_description_content, str):
        logging.debug(f'Failed getting Open Graph description: {og_description}')
        return None

    soup_match_result = re.match(r'Playlist · (?P<owner>[\w\s]+) ·', og_description_content)
    if not soup_match_result:
        logging.debug(f'Failed parsing Open Graph description: {og_description_content}')
        return None

    return soup_match_result.group('owner')


def _get_collection_owner(track_source: str) -> Optional[str]:
    match_result = re.match(COLLECTION_TRACK_SOURCE_REGEX, track_source)
    if not match_result:
        logging.debug(f'TrackSource is not a Spotify collection: {track_source}')
        return None
    user_id = match_result.group('user_id')

    try:
        user_response = requests.get(f'https://open.spotify.com/user/{user_id}')
    except requests.exceptions.RequestException as e:
        logging.debug(f'Spotify user request failed with the following exception: {e}')
        return None
    if user_response.status_code != HTTPStatus.OK:
        logging.debug(f'Spotify user request failed with status code {user_response.status_code}')
        return None

    soup = BeautifulSoup(user_response.text, 'html.parser')
    og_title = soup.find('meta', property='og:title')
    og_title_content = og_title.get('content') if og_title else None
    if not isinstance(og_title_content, str):
        logging.debug(f'Failed getting Open Graph title: {og_title}')
        return None

    return og_title_content


def _get_collection_artist(track_source: str) -> Optional[str]:
    match_result = re.match(COLLECTION_TRACK_SOURCE_REGEX, track_source)
    artist_id = match_result.group('artist_id') if match_result else None
    if not artist_id:
        logging.debug(f'TrackSource is not a Spotify collection filtered by artist: {track_source}')
        return None

    try:
        artist_response = requests.get(f'https://open.spotify.com/artist/{artist_id}')
    except requests.exceptions.RequestException as e:
        logging.debug(f'Spotify artist request failed with the following exception: {e}')
        return None
    if artist_response.status_code != HTTPStatus.OK:
        logging.debug(f'Spotify artist request failed with status code {artist_response.status_code}')
        return None

    soup = BeautifulSoup(artist_response.text, 'html.parser')
    og_title = soup.find('meta', property='og:title')
    og_title_content = og_title.get('content') if og_title else None
    if not isinstance(og_title_content, str):
        logging.debug(f'Failed getting Open Graph title: {og_title}')
        return None

    return og_title_content


def get_playlist_string(track_source: str, known_playlist_name: Optional[str] = None) -> Optional[str]:
    playlist_name = known_playlist_name or _get_collection_artist(track_source)
    playlist_owner = (_get_playlist_owner(track_source) or _get_collection_owner(track_source)) if playlist_name else None
    return f"{playlist_name} by {playlist_owner}" if playlist_owner else playlist_name
