# -*- coding: utf-8 -*-
import unittest
from steam.vdf import parse_text_vdf


class TextVdfTest(unittest.TestCase):
    def test_nested_and_escapes(self):
        text = '''
        "libraryfolders"
        {
            "0"
            {
                "path"  "C:\\\\Program Files (x86)\\\\Steam"
                "apps"
                {
                    "228980"  "1011723081"
                    "431960"  "829009548"
                }
            }
        }
        '''
        d = parse_text_vdf(text)
        lf = d["libraryfolders"]
        self.assertEqual(lf["0"]["path"], "C:\\Program Files (x86)\\Steam")
        self.assertEqual(set(lf["0"]["apps"].keys()), {"228980", "431960"})
        self.assertEqual(lf["0"]["apps"]["431960"], "829009548")

    def test_line_comments_ignored(self):
        text = '"AppState"\n{\n  // a comment\n  "name" "Wallpaper Engine"\n}\n'
        d = parse_text_vdf(text)
        self.assertEqual(d["AppState"]["name"], "Wallpaper Engine")

    def test_empty_block(self):
        d = parse_text_vdf('"root"\n{\n  "apps"\n  {\n  }\n}\n')
        self.assertEqual(d["root"]["apps"], {})


if __name__ == "__main__":
    unittest.main()
