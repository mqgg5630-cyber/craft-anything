import unittest

from relay import image_candidates, image_token, image_urls_from_html, safe_note_id


class RelayParsingTests(unittest.TestCase):
    def test_extracts_only_note_image_urls_and_deduplicates_variants(self):
        page = r'''<script>window.__INITIAL_STATE__={"note":{"imageList":[
          {"urlDefault":"https:\\u002F\\u002Fsns-web-i10.rednotecdn.com\\u002F2026\\u002Fsig\\u002Fspectrum\\u002F1040abc!nd_dft_wlteh_webp_3","urlPre":"https:\\u002F\\u002Fsns-web-i10.rednotecdn.com\\u002F2026\\u002Fsig\\u002Fspectrum\\u002F1040abc!nd_dft_wlteh_webp_3"},
          {"urlDefault":"https:\\u002F\\u002Fsns-web-i10.rednotecdn.com\\u002F2026\\u002Fsig\\u002Fnotes_pre_post\\u002F1040def!nd_dft_wlteh_webp_3"}
        ]}}</script>'''
        urls = image_urls_from_html(page)
        self.assertEqual(len(urls), 2)
        self.assertTrue(image_token(urls[0]).endswith("spectrum/1040abc"))
        self.assertTrue(image_token(urls[1]).endswith("notes_pre_post/1040def"))

    def test_builds_original_candidates_from_signed_preview(self):
        url = "https://sns-web-i10.rednotecdn.com/2026/sig/spectrum/1040abc!nd_dft_wlteh_webp_3"
        candidates = image_candidates(url)
        self.assertTrue(any("sns-img-bd.xhscdn.com/spectrum/1040abc" in item for item in candidates))
        self.assertTrue(any("ci.xiaohongshu.com/spectrum/1040abc" in item for item in candidates))

    def test_extracts_note_id_without_retaining_query_token(self):
        self.assertEqual(safe_note_id("https://www.xiaohongshu.com/explore/0123456789abcdef01234567?xsec_token=secret"), "0123456789abcdef01234567")


if __name__ == "__main__":
    unittest.main()
