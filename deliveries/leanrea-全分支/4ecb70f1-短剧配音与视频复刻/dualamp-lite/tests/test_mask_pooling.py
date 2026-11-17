"""V4 test 7: masked max pooling ignores padding and rejects empty masks."""

import unittest

import torch

from dualamp_lite.v4.models import M2, M3, masked_max


class MaskPoolingTest(unittest.TestCase):
    def test_masked_max_ignores_padding(self):
        x = torch.tensor([[[1.0, 5.0, 100.0]]])
        mask = torch.tensor([[True, True, False]])
        self.assertEqual(float(masked_max(x, mask)), 5.0)

    def test_masked_max_handles_several_channels(self):
        x = torch.tensor([[[1.0, 2.0], [3.0, -1.0]]])
        mask = torch.tensor([[True, False]])
        out = masked_max(x, mask)
        self.assertEqual(out.shape, (1, 2))
        self.assertEqual(out.tolist(), [[1.0, 3.0]])

    def test_all_padding_raises(self):
        with self.assertRaises(ValueError):
            masked_max(torch.zeros(1, 4, 5), torch.zeros(1, 5, dtype=torch.bool))

    def test_padding_content_does_not_change_the_logits(self):
        torch.manual_seed(0)
        for klass in (M2, M3):
            model = klass(embed_dim=16, n_phys=32, dropout=0.0).eval()
            residue = torch.randn(2, 6, 16)
            mask = torch.tensor([[True] * 4 + [False] * 2, [True] * 6])
            phys = torch.randn(2, 32)
            with torch.no_grad():
                a = model(phys=phys, residue=residue, mask=mask)
                dirty = residue.clone()
                dirty[0, 4:] = 1e3
                b = model(phys=phys, residue=dirty, mask=mask)
            torch.testing.assert_close(a, b, rtol=0, atol=0)


if __name__ == "__main__":
    unittest.main()
