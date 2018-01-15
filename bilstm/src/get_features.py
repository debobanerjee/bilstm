"""Image feature extraction."""
import os
import sys
import json
import time
import h5py
import torch
from model import FullBiLSTM
from datasets import PolyvoreDataset, collate_seq
from evaluation import Evaluation
from utils import ImageTransforms

def GetFeatures(model_name, feats_filename):
    """Main function for feature extraction."""

    batch_size = 1

    model = FullBiLSTM(512, 512, 2480, batch_first=True, dropout=0.7)
    evaluator = Evaluation(model, model_name, '../data/images',
                           batch_first=True, cuda=True)

    json_filenames = {'train': 'train_no_dup.json',
                      'test': 'test_no_dup.json',
                      'val': 'valid_no_dup.json'}

    img_dir, json_dir = '../data/images', '../data/label'
    dataloaders = {x: torch.utils.data.DataLoader(
        PolyvoreDataset(os.path.join(json_dir, json_filenames[x]), img_dir,
                        img_transform=None, txt_transform=None),
        batch_size=batch_size,
        shuffle=False, num_workers=4,
        collate_fn=collate_seq)
                   for x in ['test']}

    test_files = json.load(open(os.path.join(json_dir, json_filenames['test'])))

    filenames = []
    features = torch.Tensor().cuda()

    tic = time.time()
    for i, (test_file, batch) in enumerate(zip(test_files, dataloaders['test'])):
        sys.stdout.write("%d/%d sets - %.2f secs elapsed\r" % (i, len(test_files), time.time() - tic))
        sys.stdout.flush()
        set_id = test_file['set_id']
        im_idxs = [x['index'] for x in test_file['items']]
        im_feats = evaluator.get_img_feats(batch[0]['images'])
        for idx in im_idxs:
            filenames.append(set_id + '_' + str(idx))
        features = torch.cat((features, im_feats.data))
        for ignored in batch[0]['ignored']:
            filenames.remove(ignored)
    if not os.path.exists(os.path.dirname(feats_filename)):
        os.makedirs(os.path.dirname(feats_filename))
    filenames = [n.encode("ascii", "ignore") for n in filenames]
    savefile = h5py.File(feats_filename, 'w')
    savefile.create_dataset('filenames', data=filenames)
    savefile.create_dataset('features', data=features)
    savefile.close()

if __name__ == '__main__':
    model_name = '../models/shuffle_500'
    feats_filename = '../data/feats_shuffle_500.h5'
    GetFeatures(model_name, feats_filename)