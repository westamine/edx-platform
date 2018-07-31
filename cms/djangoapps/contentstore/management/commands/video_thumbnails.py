"""
Command to add thumbnails to videos.
"""

import logging
from django.core.management import BaseCommand
from edxval.api import get_all_videos
from openedx.core.djangoapps.video_config.models import VideoThumbnailSetting, UpdatedVideos
from cms.djangoapps.contentstore.tasks import enqueue_update_thumbnail_tasks

log = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Example usage:
        $ ./manage.py cms video_thumbnails --from-settings
    """
    help = 'Adds thumbnails from YouTube to videos'

    def add_arguments(self, parser):
        """
        Add arguments to the command parser.
        """
        parser.add_argument(
            '--from-settings', '--from_settings',
            dest='from_settings',
            help='Update videos with settings set via django admin',
            action='store_true',
            default=False,
        )

    def _get_command_options(self, options):
        """
        Returns the command arguments configured via django admin.
        """
        command_settings = self._latest_settings()
        if command_settings.all_videos:
            #TODO update with actual VAL api
            all_video_ids = [video.edx_video_id for video in get_all_videos().iterator()]

            updated_videos = UpdatedVideos.objects.all().values_list('video_id', flat=True)
            non_updated_videos = [
                video_id
                for video_id in all_video_ids
                if video_id not in updated_videos
            ]
            # Video batch to be updated
            video_batch = non_updated_videos[:command_settings.batch_size]

            log.info(
                ('[Video Thumbnails] Videos(total): %s, '
                 'Videos(updated): %s, Videos(non-updated): %s, '
                 'Videos(updation-in-process): %s'),
                len(all_video_ids),
                len(updated_videos),
                len(non_updated_videos),
                len(video_batch),
            )
        else:
            video_batch = command_settings.video_ids.split()
            force_update = command_settings.force_update
            commit = command_settings.commit

        return video_batch, force_update, commit

    def _latest_settings(self):
        """
        Return the latest version of the VideoThumbnailSetting
        """
        return VideoThumbnailSetting.current()

    def handle(self, *args, **options):
        """
        Invokes the video thumbnail enqueue function.
        """
        command_settings = self._latest_settings()
        video_batch, force_update, commit = self._get_command_options(options)
        command_run = command_settings.increment_run() if commit else -1
        enqueue_update_thumbnail_tasks(
            video_ids=video_batch, commit=commit, command_run=command_run, force_update=force_update
        )

        if commit and options.get('from_settings') and command_settings.all_videos:
            UpdatedVideos.objects.bulk_create([
                UpdatedVideos(video_id=video_id, command_run=command_run)
                for video_id in video_batch
            ])
