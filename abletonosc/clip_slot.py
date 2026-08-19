from typing import Tuple, Any
from .handler import AbletonOSCHandler

class ClipSlotHandler(AbletonOSCHandler):
    def __init__(self, manager):
        super().__init__(manager)
        self.class_identifier = "clip_slot"

    def init_api(self):
        def create_clip_slot_callback(func, *args, pass_clip_index=False):
            def clip_slot_callback(params: Tuple[Any]):
                track_index, clip_index = int(params[0]), int(params[1])
                #--------------------------------------------------------------------------------
                # PATCHED (Konversation vom 19.08.2026):
                # track_index/clip_index can be out of range if the track/scene count has
                # shrunk since a listener was registered on this cell (e.g. a track was
                # deleted). Previously this raised an unhandled IndexError here, before
                # _stop_listen was ever reached -- meaning the original listener was never
                # removed and a later start_listen on the same (now differently-occupied)
                # cell left two live listeners bound to the same clip slot. Analogous to the
                # fix in track.py::create_track_callback. _stop_listen (handler.py) no longer
                # needs a valid clip_slot to remove the correct listener -- it uses the object
                # stored at start_listen time -- so pass None through instead of crashing;
                # other callbacks (get/set/methods, start_listen) will still fail on a None
                # target, but gracefully, one level up.
                #--------------------------------------------------------------------------------
                try:
                    track = self.song.tracks[track_index]
                    clip_slot = track.clip_slots[clip_index]
                except IndexError:
                    clip_slot = None

                if pass_clip_index:
                    rv = func(clip_slot, *args, tuple(params[0:]))
                else:
                    rv = func(clip_slot, *args, tuple(params[2:]))

                self.logger.info(track_index, clip_index, rv)
                if rv is not None:
                    return (track_index, clip_index, *rv)

            return clip_slot_callback

        methods = [
            "fire",
            "stop",
            "create_clip",
            "delete_clip"
        ]
        properties_r = [
            "has_clip",
            "controls_other_clips",
            "is_group_slot",
            "is_playing",
            "is_triggered",
            "playing_status",
            "will_record_on_start",
        ]
        properties_rw = [
            "has_stop_button"
        ]

        for method in methods:
            self.osc_server.add_handler("/live/clip_slot/%s" % method,
                                        create_clip_slot_callback(self._call_method, method))

        for prop in properties_r + properties_rw:
            self.osc_server.add_handler("/live/clip_slot/get/%s" % prop,
                                        create_clip_slot_callback(self._get_property, prop))
            self.osc_server.add_handler("/live/clip_slot/start_listen/%s" % prop,
                                        create_clip_slot_callback(self._start_listen, prop, pass_clip_index=True))
            self.osc_server.add_handler("/live/clip_slot/stop_listen/%s" % prop,
                                        create_clip_slot_callback(self._stop_listen, prop, pass_clip_index=True))
        for prop in properties_rw:
            self.osc_server.add_handler("/live/clip_slot/set/%s" % prop,
                                        create_clip_slot_callback(self._set_property, prop))

        def duplicate_clip_slot(clip_slot, args):
            target_track_index, target_clip_index = tuple(args)
            track = self.song.tracks[target_track_index]
            target_clip_slot = track.clip_slots[target_clip_index]
            clip_slot.duplicate_clip_to(target_clip_slot)

        self.osc_server.add_handler("/live/clip_slot/duplicate_clip_to", create_clip_slot_callback(duplicate_clip_slot))
