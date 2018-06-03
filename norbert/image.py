import numpy as np
from PIL import Image
import tempfile as tmp
import piexif
import piexif.helper
import json

eps = np.finfo(np.float).eps


class Coder(object):
    def __init__(
        self,
        format='jpg',
        quality=75,
        qtable=None
    ):
        self.format = format
        self.quality = quality

        if qtable is not None:
            self.qtables = [qtable]
        else:
            self.qtables = None

    def encodedecode(self, X):
        """encode/decode on the fly"""
        image_file = tmp.NamedTemporaryFile(suffix='.' + self.format)
        self.encode(X, out=image_file.name)
        Y = self.decode(image_file.name)
        image_file.close()
        return Y

    def encode(self, X, out, user_comment_dict=None):
        """
        Input is (nb_frames, nb_bins, nb_channels)
        Pillow takes (img_height, img_width, channels),
        so we reshape
            nb_frames -> img_width
            nb_bins --> img_height
            nb_channels -> channel
        """

        buf = np.squeeze(X)
        # swap frames and bins
        buf = buf.swapaxes(0, 1)
        # flip so that image is low_frequency at the bottom
        buf = buf[::-1, ...]

        if buf.ndim <= 2:
            img = Image.fromarray(buf.astype(np.int8), 'L')
        else:
            # stack channels into red and green, not using blue
            buf = np.concatenate((buf, np.zeros(buf.shape[:-1] + (1,))), -1)
            img = Image.fromarray(buf.astype(np.int8), 'RGB')

        if user_comment_dict is not None:
            user_comment = piexif.helper.UserComment.dump(
                json.dumps(user_comment_dict)
            )
            exif_ifd = {
                piexif.ExifIFD.UserComment: user_comment,
            }
            exif_dict = {"Exif": exif_ifd}
            exif_bytes = piexif.dump(exif_dict)
            img.save(
                out,
                quality=self.quality,
                optimize=True,
                exif=exif_bytes,
                qtables=self.qtables,
                subsampling=0
            )
        else:
            img.save(
                out,
                quality=self.quality,
                optimize=True,
                qtables=self.qtables,
                subsampling=0
            )

    def decode(self, buf):
        img = Image.open(buf)
        img = np.array(img).astype(np.uint8)
        # inverse flipped image
        img = img[::-1, ...]
        if img.ndim <= 2:
            return np.atleast_3d(img).swapaxes(0, 1)
        else:
            img = img.swapaxes(0, 1)
            # select only red and blue channels
            return img[:, :, [0, 1]]
