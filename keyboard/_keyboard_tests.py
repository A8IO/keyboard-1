# -*- coding: utf-8 -*-
"""
Side effects are avoided using two techniques:

- Low level OS requests (keyboard._os_keyboard) are mocked out by rewriting
the functions at that namespace. This includes a list of dummy keys.
- Events are pumped manually by the main test class, and accepted events
are tested against expected values.

Fake user events are appended to `input_events`, passed through
keyboard,_listener.direct_callback, then, if accepted, appended to
`output_events`. Fake OS events (keyboard.press) are processed
and added to `output_events` immediately, mimicking real functionality.
"""
import unittest
import time

import keyboard
from ._keyboard_event import KeyboardEvent, KEY_DOWN, KEY_UP

dummy_keys = {
    'space': [(0, [])],

    'a': [(1, [])],
    'b': [(2, [])],
    'c': [(3, [])],
    'A': [(1, ['shift']), (-1, [])],
    'B': [(2, ['shift']), (-2, [])],
    'C': [(3, ['shift']), (-3, [])],

    'alt': [(4, [])],
    'left alt': [(4, [])],

    'left shift': [(5, [])],
    'right shift': [(6, [])],

    'left ctrl': [(7, [])],

    'backspace': [(8, [])],
    'caps lock': [(9, [])],

    '+': [(10, [])],
    ',': [(11, [])],
    '_': [(12, [])],
}

def make_event(event_type, name, scan_code=None, time=0):
    return KeyboardEvent(event_type=event_type, scan_code=scan_code or dummy_keys[name][0][0], name=name, time=time)

# Used when manually pumping events.
input_events = []
output_events = []

def send_instant_event(event):
    if keyboard._listener.direct_callback(event):
        output_events.append(event)

# Mock out side effects.
keyboard._os_keyboard.init = lambda: None
keyboard._os_keyboard.listen = lambda callback: None
keyboard._os_keyboard.map_name = dummy_keys.__getitem__
keyboard._os_keyboard.press = lambda scan_code: send_instant_event(make_event(KEY_DOWN, None, scan_code))
keyboard._os_keyboard.release = lambda scan_code: send_instant_event(make_event(KEY_UP, None, scan_code))
keyboard._os_keyboard.type_unicode = lambda char: output_events.append(KeyboardEvent(event_type=KEY_DOWN, scan_code=999, name=char))

# Shortcuts for defining test inputs and expected outputs.
# Usage: d_shift + d_a + u_a + u_shift
d_a = [make_event(KEY_DOWN, 'a')]
u_a = [make_event(KEY_UP, 'a')]
du_a = d_a+u_a
d_b = [make_event(KEY_DOWN, 'b')]
u_b = [make_event(KEY_UP, 'b')]
du_b = d_b+u_b
d_c = [make_event(KEY_DOWN, 'c')]
u_c = [make_event(KEY_UP, 'c')]
du_c = d_c+u_c
d_ctrl = [make_event(KEY_DOWN, 'left ctrl')]
u_ctrl = [make_event(KEY_UP, 'left ctrl')]
du_ctrl = d_ctrl+u_ctrl
d_shift = [make_event(KEY_DOWN, 'left shift')]
u_shift = [make_event(KEY_UP, 'left shift')]
du_shift = d_shift+u_shift
d_alt = [make_event(KEY_DOWN, 'alt')]
u_alt = [make_event(KEY_UP, 'alt')]
du_alt = d_alt+u_alt
du_backspace = [make_event(KEY_DOWN, 'backspace'), make_event(KEY_UP, 'backspace')]
du_capslock = [make_event(KEY_DOWN, 'caps lock'), make_event(KEY_UP, 'caps lock')]
du_space = [make_event(KEY_DOWN, 'space'), make_event(KEY_UP, 'space')]

triggered = [KeyboardEvent(KEY_DOWN, scan_code=999)]

class TestKeyboard(unittest.TestCase):
    def tearDown(self):
        keyboard.unhook_all()
        del input_events[:]
        del output_events[:]
        keyboard._recording = None
        keyboard._pressed_events.clear()
        keyboard._listener.init()

    def do(self, manual_events, expected=None):
        input_events.extend(manual_events)
        while input_events:
            event = input_events.pop(0)
            if keyboard._listener.direct_callback(event):
                output_events.append(event)
        if expected:
            self.assertListEqual(output_events, expected)
        del output_events[:]

        keyboard._listener.queue.join()

    def test_event_json(self):
        event = make_event(KEY_DOWN, u'á \'"', 999)
        import json
        self.assertEqual(event, KeyboardEvent(**json.loads(event.to_json())))

    def test_is_modifier_name(self):
        for name in keyboard.all_modifiers:
            self.assertTrue(keyboard.is_modifier(name))
    def test_is_modifier_scan_code(self):
        for i in range(10):
            self.assertEqual(keyboard.is_modifier(i), i in [4, 5, 6, 7])

    def test_key_to_scan_codes_brute(self):
        for name, entries in dummy_keys.items():
            expected = tuple(scan_code for scan_code, modifiers in entries)
            self.assertEqual(keyboard.key_to_scan_codes(name), expected)
    def test_key_to_scan_code_from_scan_code(self):
        for i in range(10):
            self.assertEqual(keyboard.key_to_scan_codes(i), (i,))
    def test_key_to_scan_code_from_letter(self):
        self.assertEqual(keyboard.key_to_scan_codes('a'), (1,))
        self.assertEqual(keyboard.key_to_scan_codes('A'), (1,-1))
    def test_key_to_scan_code_from_normalized(self):
        self.assertEqual(keyboard.key_to_scan_codes('shift'), (5,6))
        self.assertEqual(keyboard.key_to_scan_codes('SHIFT'), (5,6))
        self.assertEqual(keyboard.key_to_scan_codes('ctrl'), keyboard.key_to_scan_codes('CONTROL'))
    def test_key_to_scan_code_from_sided_modifier(self):
        self.assertEqual(keyboard.key_to_scan_codes('left shift'), (5,))
        self.assertEqual(keyboard.key_to_scan_codes('right shift'), (6,))
    def test_key_to_scan_code_underscores(self):
        self.assertEqual(keyboard.key_to_scan_codes('_'), (12,))
        self.assertEqual(keyboard.key_to_scan_codes('right_shift'), (6,))
    def test_key_to_scan_code_error_none(self):
        with self.assertRaises(ValueError):
            keyboard.key_to_scan_codes(None)
    def test_key_to_scan_code_error_empty(self):
        with self.assertRaises(ValueError):
            keyboard.key_to_scan_codes('')
    def test_key_to_scan_code_error_other(self):
        with self.assertRaises(ValueError):
            keyboard.key_to_scan_codes({})
    def test_key_to_scan_code_list(self):
        self.assertEqual(keyboard.key_to_scan_codes([10, 5, 'a']), (10, 5, 1))
            

    def test_parse_hotkey_simple(self):
        self.assertEqual(keyboard.parse_hotkey('a'), (((1,),),))
        self.assertEqual(keyboard.parse_hotkey('A'), (((1,-1),),))
    def test_parse_hotkey_separators(self):
        self.assertEqual(keyboard.parse_hotkey('+'), keyboard.parse_hotkey('plus'))
        self.assertEqual(keyboard.parse_hotkey(','), keyboard.parse_hotkey('comma'))
    def test_parse_hotkey_keys(self):
        self.assertEqual(keyboard.parse_hotkey('left shift + a'), (((5,), (1,),),))
        self.assertEqual(keyboard.parse_hotkey('left shift+a'), (((5,), (1,),),))
    def test_parse_hotkey_simple_steps(self):
        self.assertEqual(keyboard.parse_hotkey('a,b'), (((1,),),((2,),)))
        self.assertEqual(keyboard.parse_hotkey('a, b'), (((1,),),((2,),)))
    def test_parse_hotkey_steps(self):
        self.assertEqual(keyboard.parse_hotkey('a+b, b+c'), (((1,),(2,)),((2,),(3,))))

    def test_is_pressed_none(self):
        self.assertFalse(keyboard.is_pressed('a'))
    def test_is_pressed_true(self):
        self.do(d_a)
        self.assertTrue(keyboard.is_pressed('a'))
    def test_is_pressed_true_scan_code_true(self):
        self.do(d_a)
        self.assertTrue(keyboard.is_pressed(1))
    def test_is_pressed_true_scan_code_false(self):
        self.do(d_a)
        self.assertFalse(keyboard.is_pressed(2))
    def test_is_pressed_true_scan_code_invalid(self):
        self.do(d_a)
        self.assertFalse(keyboard.is_pressed(-1))
    def test_is_pressed_false(self):
        self.do(d_a+u_a+d_b)
        self.assertFalse(keyboard.is_pressed('a'))
        self.assertTrue(keyboard.is_pressed('b'))
    def test_is_pressed_hotkey_true(self):
        self.do(d_shift+d_a)
        self.assertTrue(keyboard.is_pressed('shift+a'))
    def test_is_pressed_hotkey_false(self):
        self.do(d_shift+d_a+u_a)
        self.assertFalse(keyboard.is_pressed('shift+a'))
    def test_is_pressed_multi_step_fail(self):
        self.do(u_a+d_a)
        with self.assertRaises(ValueError):
            keyboard.is_pressed('a, b')

    def test_send_single_press_release(self):
        keyboard.send('a', do_press=True, do_release=True)
        self.do([], d_a+u_a)
    def test_send_single_press(self):
        keyboard.send('a', do_press=True, do_release=False)
        self.do([], d_a)
    def test_send_single_release(self):
        keyboard.send('a', do_press=False, do_release=True)
        self.do([], u_a)
    def test_send_single_none(self):
        keyboard.send('a', do_press=False, do_release=False)
        self.do([], [])
    def test_press(self):
        keyboard.press('a')
        self.do([], d_a)
    def test_release(self):
        keyboard.release('a')
        self.do([], u_a)
    def test_press_and_release(self):
        keyboard.press_and_release('a')
        self.do([], d_a+u_a)

    def test_send_modifier_press_release(self):
        keyboard.send('ctrl+a', do_press=True, do_release=True)
        self.do([], d_ctrl+d_a+u_a+u_ctrl)
    def test_send_modifiers_release(self):
        keyboard.send('ctrl+shift+a', do_press=False, do_release=True)
        self.do([], u_a+u_shift+u_ctrl)

    def test_call_later(self):
        triggered = []
        def trigger(arg1, arg2):
            assert arg1 == 1 and arg2 == 2
            triggered.append(True)
        keyboard.call_later(trigger, (1, 2), 0.01)
        self.assertFalse(triggered)
        time.sleep(0.05)
        self.assertTrue(triggered)

    def test_hook_nonblocking(self):
        self.i = 0
        def count(e):
            self.assertEqual(e.name, 'a')
            self.i += 1
        keyboard.hook(count, suppress=False)
        self.do(d_a+u_a, d_a+u_a)
        self.assertEqual(self.i, 2)
        keyboard.unhook(count)
        self.do(d_a+u_a, d_a+u_a)
        self.assertEqual(self.i, 2)
        keyboard.hook(count, suppress=False)
        self.do(d_a+u_a, d_a+u_a)
        self.assertEqual(self.i, 4)
        keyboard.unhook_all()
        self.do(d_a+u_a, d_a+u_a)
        self.assertEqual(self.i, 4)
    def test_hook_blocking(self):
        self.i = 0
        def count(e):
            self.assertIn(e.name, ['a', 'b'])
            self.i += 1
            return e.name == 'b'
        keyboard.hook(count, suppress=True)
        self.do(d_a+d_b, d_b)
        self.assertEqual(self.i, 2)
        keyboard.unhook(count)
        self.do(d_a+d_b, d_a+d_b)
        self.assertEqual(self.i, 2)
        keyboard.hook(count, suppress=True)
        self.do(d_a+d_b, d_b)
        self.assertEqual(self.i, 4)
        keyboard.unhook_all()
        self.do(d_a+d_b, d_a+d_b)
        self.assertEqual(self.i, 4)
    def test_on_press_nonblocking(self):
        keyboard.on_press(lambda e: self.assertEqual(e.name, 'a') and self.assertEqual(e.event_type, KEY_DOWN))
        self.do(d_a+u_a)
    def test_on_press_blocking(self):
        keyboard.on_press(lambda e: e.scan_code == 1, suppress=True)
        self.do([make_event(KEY_DOWN, 'A', -1)] + d_a, d_a)
    def test_on_release(self):
        keyboard.on_release(lambda e: self.assertEqual(e.name, 'a') and self.assertEqual(e.event_type, KEY_UP))
        self.do(d_a+u_a)

    def test_hook_key_invalid(self):
        with self.assertRaises(ValueError):
            keyboard.hook_key('invalid', lambda e: None)
    def test_hook_key_nonblocking(self):
        self.i = 0
        def count(event):
            self.i += 1
        keyboard.hook_key('A', count)
        self.do(d_a)
        self.assertEqual(self.i, 1)
        self.do(u_a+d_b)
        self.assertEqual(self.i, 2)
        self.do([make_event(KEY_DOWN, 'A', -1)])
        self.assertEqual(self.i, 3)
        keyboard.unhook_key('A')
        self.do(d_a)
        self.assertEqual(self.i, 3)
    def test_hook_key_blocking(self):
        self.i = 0
        def count(event):
            self.i += 1
            return event.scan_code == 1
        keyboard.hook_key('A', count, suppress=True)
        self.do(d_a, d_a)
        self.assertEqual(self.i, 1)
        self.do(u_a+d_b, u_a+d_b)
        self.assertEqual(self.i, 2)
        self.do([make_event(KEY_DOWN, 'A', -1)], [])
        self.assertEqual(self.i, 3)
        keyboard.unhook_key('A')
        self.do([make_event(KEY_DOWN, 'A', -1)], [make_event(KEY_DOWN, 'A', -1)])
        self.assertEqual(self.i, 3)
    def test_on_press_key_nonblocking(self):
        keyboard.on_press_key('A', lambda e: self.assertEqual(e.name, 'a') and self.assertEqual(e.event_type, KEY_DOWN))
        self.do(d_a+u_a+d_b+u_b)
    def test_on_press_key_blocking(self):
        keyboard.on_press_key('A', lambda e: e.scan_code == 1, suppress=True)
        self.do([make_event(KEY_DOWN, 'A', -1)] + d_a, d_a)
    def test_on_release_key(self):
        keyboard.on_release_key('a', lambda e: self.assertEqual(e.name, 'a') and self.assertEqual(e.event_type, KEY_UP))
        self.do(d_a+u_a)

    def test_block_key(self):
        keyboard.block_key('a')
        self.do(d_a+d_b, d_b)
        self.do([make_event(KEY_DOWN, 'A', -1)], [make_event(KEY_DOWN, 'A', -1)])
        keyboard.unblock_key('a')
        self.do(d_a+d_b, d_a+d_b)
    def test_block_key_ambiguous(self):
        keyboard.block_key('A')
        self.do(d_a+d_b, d_b)
        self.do([make_event(KEY_DOWN, 'A', -1)], [])

    def test_remap_key_simple(self):
        keyboard.remap_key('a', 'b')
        self.do(d_a+d_c+u_a, d_b+d_c+u_b)
        keyboard.unremap_key('a')
        self.do(d_a+d_c+u_a, d_a+d_c+u_a)
    def test_remap_key_ambiguous(self):
        keyboard.remap_key('A', 'b')
        self.do(d_a+d_b, d_b+d_b)
        self.do([make_event(KEY_DOWN, 'A', -1)], d_b)
    def test_remap_key_multiple(self):
        keyboard.remap_key('a', 'shift+b')
        self.do(d_a+d_c+u_a, d_shift+d_b+d_c+u_b+u_shift)
        keyboard.unremap_key('a')
        self.do(d_a+d_c+u_a, d_a+d_c+u_a)

    def test_stash_state(self):
        self.do(d_a+d_shift)
        self.assertEqual(sorted(keyboard.stash_state()), [1, 5])
        self.do([], u_a+u_shift)
    def test_restore_state(self):
        self.do(d_b)
        keyboard.restore_state([1, 5])
        self.do([], u_b+d_a+d_shift)
    def test_restore_modifieres(self):
        self.do(d_b)
        keyboard.restore_modifiers([1, 5])
        self.do([], u_b+d_shift)

    def test_write_simple(self):
        keyboard.write('a', exact=False)
        self.do([], d_a+u_a)
    def test_write_multiple(self):
        keyboard.write('ab', exact=False)
        self.do([], d_a+u_a+d_b+u_b)
    def test_write_modifiers(self):
        keyboard.write('Ab', exact=False)
        self.do([], d_shift+d_a+u_a+u_shift+d_b+u_b)
    #def test_write_stash_not_restore(self):
    #    self.do(d_shift)
    #    keyboard.write('a', restore_state_after=False, exact=False)
    #    self.do([], u_shift+d_a+u_a)
    def test_write_stash_restore(self):
        self.do(d_shift)
        keyboard.write('a', exact=False)
        self.do([], u_shift+d_a+u_a+d_shift)
    def test_write_multiple(self):
        last_time = time.time()
        keyboard.write('ab', delay=0.01, exact=False)
        self.do([], d_a+u_a+d_b+u_b)
        self.assertGreater(time.time() - last_time, 0.015)
    def test_write_unicode_explicit(self):
        keyboard.write('ab', exact=True)
        self.do([], [KeyboardEvent(event_type=KEY_DOWN, scan_code=999, name='a'), KeyboardEvent(event_type=KEY_DOWN, scan_code=999, name='b')])
    def test_write_unicode_fallback(self):
        keyboard.write(u'áb', exact=False)
        self.do([], [KeyboardEvent(event_type=KEY_DOWN, scan_code=999, name=u'á')]+d_b+u_b)

    def test_start_stop_recording(self):
        keyboard.start_recording()
        self.do(d_a+u_a)
        self.assertEqual(keyboard.stop_recording(), d_a+u_a)
    def test_stop_recording_error(self):
        with self.assertRaises(ValueError):
            keyboard.stop_recording()

    def test_play_nodelay(self):
        keyboard.play(d_a+u_a, 0)
        self.do([], d_a+u_a)
    def test_play_stash(self):
        self.do(d_ctrl)
        keyboard.play(d_a+u_a, 0)
        self.do([], u_ctrl+d_a+u_a+d_ctrl)
    def test_play_delay(self):
        last_time = time.time()
        events = [make_event(KEY_DOWN, 'a', 1, 100), make_event(KEY_UP, 'a', 1, 100.01)]
        keyboard.play(events, 1)
        self.do([], d_a+u_a)
        self.assertGreater(time.time() - last_time, 0.005)

    def test_get_typed_strings_simple(self):
        events = du_a+du_b+du_backspace+d_shift+du_a+u_shift+du_space+du_ctrl+du_a
        self.assertEqual(list(keyboard.get_typed_strings(events)), ['aA ', 'a'])
    def test_get_typed_strings_backspace(self):
        events = du_a+du_b+du_backspace
        self.assertEqual(list(keyboard.get_typed_strings(events)), ['a'])
        events = du_backspace+du_a+du_b
        self.assertEqual(list(keyboard.get_typed_strings(events)), ['ab'])
    def test_get_typed_strings_shift(self):
        events = d_shift+du_a+du_b+u_shift+du_space+du_ctrl+du_a
        self.assertEqual(list(keyboard.get_typed_strings(events)), ['AB ', 'a'])
    def test_get_typed_strings_all(self):
        events = du_a+du_b+du_backspace+d_shift+du_a+du_capslock+du_b+u_shift+du_space+du_ctrl+du_a
        self.assertEqual(list(keyboard.get_typed_strings(events)), ['aAb ', 'A'])

    def test_get_hotkey_name_simple(self):
        self.assertEqual(keyboard.get_hotkey_name(['a']), 'a')
    def test_get_hotkey_name_modifiers(self):
        self.assertEqual(keyboard.get_hotkey_name(['a', 'shift', 'ctrl']), 'ctrl+shift+a')
    def test_get_hotkey_name_normalize(self):
        self.assertEqual(keyboard.get_hotkey_name(['SHIFT', 'left ctrl']), 'ctrl+shift')
    def test_get_hotkey_name_plus(self):
        self.assertEqual(keyboard.get_hotkey_name(['+']), 'plus')
    def test_get_hotkey_name_duplicated(self):
        self.assertEqual(keyboard.get_hotkey_name(['+', 'plus']), 'plus')
    def test_get_hotkey_name_full(self):
        self.assertEqual(keyboard.get_hotkey_name(['+', 'left ctrl', 'shift', 'WIN', 'right alt']), 'ctrl+alt+shift+windows+plus')
    def test_get_hotkey_name_multiple(self):
        self.assertEqual(keyboard.get_hotkey_name(['ctrl', 'b', '!', 'a']), 'ctrl+!+a+b')
    def test_get_hotkey_name_from_pressed(self):
        self.do(du_c+d_ctrl+d_a+d_b)
        self.assertEqual(keyboard.get_hotkey_name(), 'ctrl+a+b')

    def test_read_hotkey(self):
        queue = keyboard._queue.Queue()
        def process():
            queue.put(keyboard.read_hotkey())
        from threading import Thread
        Thread(target=process).start()
        time.sleep(0.01)
        self.do(d_ctrl+d_a+d_b+u_ctrl)
        self.assertEqual(queue.get(0.5), 'ctrl+a+b')

    def test_wait_infinite(self):
        self.triggered = False
        def process():
            keyboard.wait()
            self.triggered = True
        from threading import Thread
        t = Thread(target=process)
        t.daemon = True # Yep, we are letting this thread loose.
        t.start()
        time.sleep(0.01)
        self.assertFalse(self.triggered)
        
    def test_hook_hotkey_part_suppress_single(self):
        keyboard._hook_hotkey_part('a', lambda e: keyboard.press(999), suppress=True)
        self.do(d_a, triggered)
    def test_hook_hotkey_part_suppress_with_modifiers(self):
        keyboard._hook_hotkey_part('ctrl+shift+a', lambda e: keyboard.press(999), suppress=True)
        self.do(d_ctrl+d_shift+d_a, triggered)
    def test_hook_hotkey_part_suppress_with_modifiers_fail_unrelated_modifier(self):
        keyboard._hook_hotkey_part('ctrl+shift+a', lambda e: keyboard.press(999), suppress=True)
        self.do(d_ctrl+d_shift+u_shift+d_a, d_shift+u_shift+d_ctrl+d_a)
    def test_hook_hotkey_part_suppress_with_modifiers_fail_unrelated_key(self):
        keyboard._hook_hotkey_part('ctrl+shift+a', lambda e: keyboard.press(999), suppress=True)
        self.do(d_ctrl+d_shift+du_b, d_shift+d_ctrl+du_b)
    def test_hook_hotkey_part_suppress_with_modifiers_unrelated_key(self):
        keyboard._hook_hotkey_part('ctrl+shift+a', lambda e: keyboard.press(999), suppress=True)
        self.do(d_ctrl+d_shift+du_b+d_a, d_shift+d_ctrl+du_b+triggered)
    def test_hook_hotkey_part_suppress_with_modifiers_release(self):
        keyboard._hook_hotkey_part('ctrl+shift+a', lambda e: keyboard.press(999), suppress=True)
        self.do(d_ctrl+d_shift+du_b+d_a+u_ctrl+u_shift, d_shift+d_ctrl+du_b+triggered+u_ctrl+u_shift)
    def test_hook_hotkey_part_suppress_with_modifiers_out_of_order(self):
        keyboard._hook_hotkey_part('ctrl+shift+a', lambda e: keyboard.press(999), suppress=True)
        self.do(d_shift+d_ctrl+d_a, triggered)
    #def test_hook_hotkey_part_nosuppress_single(self):
    #    keyboard._hook_hotkey_part('a', lambda e: keyboard.press(999), suppress=False)
    #    self.do(d_a, d_a+[KeyboardEvent(KEY_DOWN, scan_code=999)])

    def test_hook_hotkey_part_fail_multistep(self):
        with self.assertRaises(NotImplementedError):
            keyboard._hook_hotkey_part('a, b', lambda e: None, True)
    def test_hook_hotkey_part_fail_invalid_combination(self):
        with self.assertRaises(NotImplementedError):
            keyboard._hook_hotkey_part('a+b', lambda e: None, True)

    def test_add_hotkey_single(self):
        return True
        self.triggered = False
        def trigger(event):
            self.assertEqual(event, d_a)
            self.triggered = True
        keyboard.add_multi_step_blocking_hotkey('a', trigger)
        self.do(d_a)
        self.assertTrue(self.triggered)

if __name__ == '__main__':
    unittest.main()

exit()

class OldTests(object):
    def test_register_hotkey(self):
        self.assertFalse(self.triggers('a', [['b']]))
        self.assertTrue(self.triggers('a', [['a']]))
        self.assertTrue(self.triggers('a, b', [['a'], ['b']]))
        self.assertFalse(self.triggers('b, a', [['a'], ['b']]))
        self.assertTrue(self.triggers('a+b', [['a', 'b']]))
        self.assertTrue(self.triggers('ctrl+a, b', [['ctrl', 'a'], ['b']]))
        self.assertFalse(self.triggers('ctrl+a, b', [['ctrl'], ['a'], ['b']]))
        self.assertTrue(self.triggers('ctrl+a, b', [['a', 'ctrl'], ['b']]))
        self.assertTrue(self.triggers('ctrl+a, b, a', [['ctrl', 'a'], ['b'], ['ctrl', 'a'], ['b'], ['a']]))

    def test_remove_hotkey(self):
        keyboard.press('a')
        keyboard.add_hotkey('a', self.fail)
        keyboard.clear_all_hotkeys()
        keyboard.press('a')
        keyboard.add_hotkey('a', self.fail)
        keyboard.clear_all_hotkeys()
        keyboard.press('a')

        keyboard.clear_all_hotkeys()

        keyboard.add_hotkey('a', self.fail)
        with self.assertRaises(ValueError):
            keyboard.remove_hotkey('b')
        keyboard.remove_hotkey('a')

    def test_wait(self):
        # If this fails it blocks. Unfortunately, but I see no other way of testing.
        from threading import Thread, Lock
        lock = Lock()
        lock.acquire()
        def t():
            keyboard.wait('a')
            lock.release()
        Thread(target=t).start()
        self.click('a')
        lock.acquire()

    def test_record_play(self):
        from threading import Thread, Lock
        lock = Lock()
        lock.acquire()
        self.recorded = None
        def t():
            self.recorded = keyboard.record('esc')
            lock.release()
        Thread(target=t).start()
        self.click('a')
        self.press('shift')
        self.press('b')
        self.release('b')
        self.release('shift')
        self.press('esc')
        lock.acquire()
        expected = [(KEY_DOWN, 'a'), (KEY_UP, 'a'), (KEY_DOWN, 'shift'), (KEY_DOWN, 'b'), (KEY_UP, 'b'), (KEY_UP, 'shift'), (KEY_DOWN, 'esc')]
        for event_recorded, expected_pair in zip(self.recorded, expected):
            expected_type, expected_name = expected_pair
            self.assertEqual(event_recorded.event_type, expected_type)
            self.assertEqual(event_recorded.name, expected_name)

        keyboard._pressed_events.clear()

        keyboard.play(self.recorded, speed_factor=0)
        self.assertEqual(self.flush_events(), [(KEY_DOWN, 'a'), (KEY_UP, 'a'), (KEY_DOWN, 'shift'), (KEY_DOWN, 'b'), (KEY_UP, 'b'), (KEY_UP, 'shift'), (KEY_DOWN, 'esc')])

        keyboard.play(self.recorded, speed_factor=100)
        self.assertEqual(self.flush_events(), [(KEY_DOWN, 'a'), (KEY_UP, 'a'), (KEY_DOWN, 'shift'), (KEY_DOWN, 'b'), (KEY_UP, 'b'), (KEY_UP, 'shift'), (KEY_DOWN, 'esc')])

        # Should be ignored and not throw an error.
        keyboard.play([FakeEvent('fake type', 'a')])

    def test_word_listener_normal(self):
        keyboard.add_word_listener('bird', self.fail)
        self.click('b')
        self.click('i')
        self.click('r')
        self.click('d')
        self.click('s')
        self.click('space')
        with self.assertRaises(ValueError):
            keyboard.add_word_listener('bird', self.fail)
        keyboard.remove_word_listener('bird')

        self.triggered = False
        def on_triggered():
            self.triggered = True
        keyboard.add_word_listener('bird', on_triggered)
        self.click('b')
        self.click('i')
        self.click('r')
        self.click('d')
        self.assertFalse(self.triggered)
        self.click('space')
        self.assertTrue(self.triggered)
        keyboard.remove_word_listener('bird')

        self.triggered = False
        def on_triggered():
            self.triggered = True
        # Word listener should be case sensitive.
        keyboard.add_word_listener('Bird', on_triggered)
        self.click('b')
        self.click('i')
        self.click('r')
        self.click('d')
        self.assertFalse(self.triggered)
        self.click('space')
        self.assertFalse(self.triggered)
        self.press('shift')
        self.click('b')
        self.release('shift')
        self.click('i')
        self.click('r')
        self.click('d')
        self.click('space')
        self.assertTrue(self.triggered)
        keyboard.remove_word_listener('Bird')

    def test_word_listener_edge_cases(self):
        self.triggered = False
        def on_triggered():
            self.triggered = True
        handler = keyboard.add_word_listener('bird', on_triggered, triggers=['enter'])
        self.click('b')
        self.click('i')
        self.click('r')
        self.click('d')
        self.click('space')
        # We overwrote the triggers to remove space. Should not trigger.
        self.assertFalse(self.triggered)
        self.click('b')
        self.click('i')
        self.click('r')
        self.click('d')
        self.assertFalse(self.triggered)
        self.click('enter')
        self.assertTrue(self.triggered)
        with self.assertRaises(ValueError):
            # Must pass handler returned by function, not passed callback.
            keyboard.remove_word_listener(on_triggered)
        with self.assertRaises(ValueError):
            keyboard.remove_word_listener('birb')
        keyboard.remove_word_listener(handler)

        self.triggered = False
        # Timeout of 0 should mean "no timeout".
        keyboard.add_word_listener('bird', on_triggered, timeout=0)
        self.click('b')
        self.click('i')
        self.click('r')
        self.click('d')
        self.assertFalse(self.triggered)
        self.click('space')
        self.assertTrue(self.triggered)
        keyboard.remove_word_listener('bird')

        self.triggered = False
        keyboard.add_word_listener('bird', on_triggered, timeout=0.01)
        self.click('b')
        self.click('i')
        self.click('r')
        time.sleep(0.03)
        self.click('d')
        self.assertFalse(self.triggered)
        self.click('space')
        # Should have timed out.
        self.assertFalse(self.triggered)
        keyboard.remove_word_listener('bird')

    def test_abbreviation(self):
        keyboard.add_abbreviation('tm', 'a')
        self.press('shift')
        self.click('t')
        self.release('shift')
        self.click('space')
        self.assertEqual(self.flush_events(), []) # abbreviations should be case sensitive
        self.click('t')
        self.click('m')
        self.click('space')
        self.assertEqual(self.flush_events(), [
            (KEY_UP, 'space'),
            (KEY_DOWN, 'backspace'),
            (KEY_UP, 'backspace'),
            (KEY_DOWN, 'backspace'),
            (KEY_UP, 'backspace'),
            (KEY_DOWN, 'backspace'),
            (KEY_UP, 'backspace'),
            (KEY_DOWN, 'a'),
            (KEY_UP, 'a')])

        keyboard.add_abbreviation('TM', 'A')
        self.press('shift')
        self.click('t')
        self.release('shift')
        self.click('m')
        self.click('space')
        self.assertEqual(self.flush_events(), [])
        self.press('shift')
        self.click('t')
        self.click('m')
        self.release('shift')
        self.click('space')
        self.assertEqual(self.flush_events(), [
            (KEY_UP, 'space'),
            (KEY_DOWN, 'backspace'),
            (KEY_UP, 'backspace'),
            (KEY_DOWN, 'backspace'),
            (KEY_UP, 'backspace'),
            (KEY_DOWN, 'backspace'),
            (KEY_UP, 'backspace'),
            (KEY_DOWN, 'shift'),
            (KEY_DOWN, 'a'),
            (KEY_UP, 'a'),
            (KEY_UP, 'shift'),])

    def test_suppression(self):
        def dummy():
            pass

        keyboard.add_hotkey('z', dummy, suppress=True)
        keyboard.add_hotkey('a+b+c', dummy, suppress=True)
        keyboard.add_hotkey('a+g+h', dummy, suppress=True, timeout=0.01)

        for key in ['a', 'b', 'c']:
            self.assertFalse(self.press(key))
        for key in ['a', 'b', 'c']:
            self.assertFalse(self.release(key))

        self.assertTrue(self.click('d'))

        for key in ['a', 'b']:
            self.assertFalse(self.press(key))
        for key in ['a', 'b']:
            self.assertFalse(self.release(key))

        self.assertTrue(self.click('c'))

        for key in ['a', 'g']:
            self.assertFalse(self.press(key))
        for key in ['a', 'g']:
            self.assertFalse(self.release(key))

        time.sleep(0.03)
        self.assertTrue(self.click('h'))

        self.assertFalse(self.press('a'))
        self.assertFalse(self.press('a'))
        self.assertFalse(self.press('a'))
        self.assertFalse(self.press('a'))
        self.assertFalse(self.release('a'))

        self.assertFalse(self.press('z'))
        self.assertFalse(self.press('z'))
        self.assertFalse(self.press('z'))
        self.assertFalse(self.press('z'))
        self.assertFalse(self.release('z'))

        keyboard.remove_hotkey('a+g+h')
        keyboard.remove_hotkey('a+b+c')

        self.assertTrue(self.click('a'))

if __name__ == '__main__':
    unittest.main()