import os
import deepchem as dc
import numpy as np
import pytest

try:
    import torch
    from deepchem.models.torch_models.molformer import MoLFormer
except ModuleNotFoundError:
    pass


@pytest.mark.torch
def test_molformer_pretraining(smiles_regression_dataset,
                               smiles_multitask_regression_dataset):
    # Pretraining in MLM mode
    from deepchem.models.torch_models.molformer import MoLFormer

    model = MoLFormer(task='mlm')
    loss = model.fit(smiles_regression_dataset, nb_epoch=1)
    assert loss

    # Pretraining in Multitask Regression Mode
    model = MoLFormer(task='mtr', n_tasks=2)
    loss = model.fit(smiles_multitask_regression_dataset, nb_epoch=1)
    assert loss


@pytest.mark.torch
def test_molformer_finetuning(smiles_regression_dataset,
                              smiles_multitask_regression_dataset):

    # test regression
    model = MoLFormer(task='regression')
    loss = model.fit(smiles_regression_dataset, nb_epoch=1)
    eval_score = model.evaluate(smiles_regression_dataset,
                                metrics=dc.metrics.Metric(
                                    dc.metrics.mean_absolute_error))
    assert loss, eval_score
    prediction = model.predict(smiles_regression_dataset)
    assert prediction.shape == smiles_regression_dataset.y.shape

    # test multitask regression
    model = MoLFormer(task='mtr', n_tasks=2)
    loss = model.fit(smiles_multitask_regression_dataset, nb_epoch=1)
    eval_score = model.evaluate(smiles_multitask_regression_dataset,
                                metrics=dc.metrics.Metric(
                                    dc.metrics.mean_absolute_error))
    assert loss, eval_score
    prediction = model.predict(smiles_multitask_regression_dataset)
    assert prediction.shape == smiles_multitask_regression_dataset.y.shape

    # test classification
    y = np.random.choice([0, 1], size=(2, 1))
    smiles = [
        "CCN(CCSC)C(=O)N[C@@](C)(CC)C(F)(F)F",
        "CC1(C)CN(C(=O)Nc2cc3ccccc3nn2)C[C@@]2(CCOC2)O1"
    ]
    dataset = dc.data.NumpyDataset(X=smiles, y=y)
    model = MoLFormer(task='classification')
    loss = model.fit(dataset, nb_epoch=1)
    eval_score = model.evaluate(dataset,
                                metrics=dc.metrics.Metric(
                                    dc.metrics.recall_score))
    assert eval_score, loss
    prediction = model.predict(dataset)
    print(prediction)
    # logit scores
    print(prediction.shape, dataset.y.shape[0])
    assert prediction.shape == (dataset.y.shape[0], 2)


@pytest.mark.torch
def test_molformer_load_from_pretrained(tmpdir, smiles_regression_dataset):
    pretrain_model_dir = os.path.join(tmpdir, 'pretrain')
    finetune_model_dir = os.path.join(tmpdir, 'finetune')
    pretrain_model = MoLFormer(task='mlm', model_dir=pretrain_model_dir)
    pretrain_model.save_checkpoint()
    finetune_model = MoLFormer(task='regression', model_dir=finetune_model_dir)
    finetune_model.load_from_pretrained(pretrain_model_dir)

    # check weights match
    pretrain_model_state_dict = pretrain_model.model.state_dict()
    finetune_model_state_dict = finetune_model.model.state_dict()

    pretrain_base_model_keys = [
        key for key in pretrain_model_state_dict.keys() if 'molformer' in key
    ]
    matches = [
        torch.allclose(pretrain_model_state_dict[key],
                       finetune_model_state_dict[key])
        for key in pretrain_base_model_keys
    ]

    assert all(matches)


@pytest.mark.torch
def test_molformer_save_reload(tmpdir):
    model = MoLFormer(task='regression', model_dir=tmpdir)
    model._ensure_built()
    model.save_checkpoint()

    model_new = MoLFormer(task='regression', model_dir=tmpdir)
    model_new.restore()

    old_state = model.model.state_dict()
    new_state = model_new.model.state_dict()
    matches = [
        torch.allclose(old_state[key], new_state[key])
        for key in old_state.keys()
    ]

    # all keys values should match
    assert all(matches)
