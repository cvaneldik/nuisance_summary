from gammapy.datasets import MapDataset
from gammapy.modeling.models import (
    FoVBackgroundModel,
    Models,
    PowerLawNormSpectralModel,
    SkyModel,
    LogParabolaSpectralModel,
    SmoothBrokenPowerLawSpectralModel,
    ExpCutoffPowerLawSpectralModel, 
    create_crab_spectral_model,
    PiecewiseNormSpectralModel
)
from gammapy.modeling import Parameter, Parameters
import astropy.units as u
        
from gammapy.modeling.models.IRF import (  # ,IRFModel
    EffAreaIRFModel,
    ERecoIRFModel,
    IRFModels,
)



def load_config():
    import yaml
    import os
    from pathlib import Path
    path = os.getcwd()
    substring = "nuisance_summary"
    path = path[: path.find(substring)] + substring + "/"
    config = yaml.safe_load(Path(path + "config.yaml").read_text()) 
    
    
    colors = config['colors']
    # asimov without
    awo = [tuple(colors[0][0]), tuple(colors[0][1])]
    # asimov with 
    aw = [tuple(colors[1][0]), tuple(colors[1][1])]
    # example without
    ewo = [tuple(colors[2][0]), tuple(colors[2][1])]
    # example with 
    ew = [tuple(colors[3][0]), tuple(colors[3][1])]
    config['_colors']  = [awo, aw, ewo, ew]
    config['folder'] = config['sys']+"_"+ config['source']+"_" +config['model'] 
    
    return config


config = load_config()
case = config["case"]
path = config[case]["path"]
figformat = config["figformat"]
path_pksflare = config[case]["path_pksflare"]


def get_path(source):
    return path_pksflare


def create_asimov(model, source, parameters=None, livetime=None, spatial_model = None):
    path = get_path(source)
    models = set_model(path, model)

    if livetime is not None:
        model = livetime
    if source == "MSH":
        dataset = MapDataset.read(f"{path}/Dataset/datasets/dataset-msh-simulated-{model}.fits.gz")
        print("loaded dataset:")
        print(f"{path}/Dataset/datasets/dataset-MSH-simulated-{model}.fits.gz")
    if source == "PKSflare":
        dataset = MapDataset.read(f"{path}/Dataset/datasets/dataset-simulated-{model}.fits.gz")
        print("loaded dataset:")
        print(f"{path}/Dataset/datasets/dataset-simulated-{model}.fits.gz")
    if parameters is not None:
        for p in parameters:
            models.parameters[p.name].value = p.value
            models.parameters[p.name].error = p.error
    if spatial_model is not None:
        models[0].spatial_model = spatial_model
    bkg_model = FoVBackgroundModel(dataset_name=dataset.name)
    bkg_model.parameters["tilt"].frozen = False
    models.append(bkg_model)
    dataset.models = models
    dataset.counts = dataset.npred()
    return dataset


def set_model(path, model):
    if model == 'crab':
        model_crab =create_crab_spectral_model(reference="hess_ecpl")
        skymodelpl = Models.read(f"{path}/Dataset/models/model-pl.yaml").copy()[0]
        skymodel = Models([SkyModel(spatial_model = skymodelpl.spatial_model,
                            spectral_model = model_crab,
                            name = "Crab")])
    elif "crab_break" in model:
       
        model_crab = SmoothBrokenPowerLawSpectralModel(amplitude = 3.35e-10 *u.Unit(" 1 / (cm2 s TeV)"), 
                                              index1 = 1.61, 
                                              index2 = 2.95, 
                                               ebreak = 0.33*u.TeV,
                                               beta = 1.73
                                              )
        skymodelpl = Models.read(f"{path}/Dataset/models/model-pl.yaml").copy()[0]
        skymodel = Models([SkyModel(spatial_model = skymodelpl.spatial_model,
                            spectral_model = model_crab,
                            name = "Crabbreak")])
        if model == "crab_break_1f":
            skymodel.parameters['index1'].frozen = True
        if model == "crab_break_ef":
            skymodel.parameters['index1'].frozen = True
            skymodel.parameters['ebreak'].frozen = True
            skymodel.parameters['beta'].frozen = False
    elif model == "crab_log":
        model_crab = LogParabolaSpectralModel(amplitude = 3.85e-11*u.Unit(" 1 / (cm2 s TeV)"),
                                   alpha = 2.51,
                                   beta = 0.24,
                                   reference = 1*u.TeV)
        skymodelpl = Models.read(f"{path}/Dataset/models/model-pl.yaml").copy()[0]
        skymodel = Models([SkyModel(spatial_model = skymodelpl.spatial_model,
                            spectral_model = model_crab,
                            name = "Crablog")])
    elif model == "crab_cutoff":
        model_crab = ExpCutoffPowerLawSpectralModel(amplitude =  3.85e-11*u.Unit(" 1 / (cm2 s TeV)"),
                                             index = 2.3,
                                             cutoff = 1/10 /u.TeV)
        skymodelpl = Models.read(f"{path}/Dataset/models/model-pl.yaml").copy()[0]
        skymodel = Models([SkyModel(spatial_model = skymodelpl.spatial_model,
                            spectral_model = model_crab,
                            name = "Crablog")])
    else:
        skymodel = Models.read(f"{path}/Dataset/models/model-{model}.yaml")#.copy()
        
    return skymodel


def load_dataset_N(dataset_empty, path, bkg_sys=False, energy = None):
    models_load = Models.read(path).copy()
    Source = models_load.names[0]
    models = Models(models_load[Source].copy())
    dataset_read = dataset_empty.copy()
    if bkg_sys:
        import operator
        
        l = len(energy)
        norms = Parameters([Parameter ("norm"+str(i), value = 0, frozen = False) for i in range(l)])
        piece = PiecewiseNormSpectralModel(energy = energy,
                                  norms = norms,
                                  interp="lin")
        bkg = FoVBackgroundModel(spectral_model = piece,
                                       dataset_name=dataset_read.name)

    else:
        bkg = FoVBackgroundModel(dataset_name=dataset_read.name)
    models.append(bkg)

    for p in bkg.parameters:
        p.value = models_load.parameters[p.name].value
        p.error = models_load.parameters[p.name].error
    for m in models_load:
        if m.type == "irf":
            irf = IRFModels(
                    e_reco_model=m.e_reco_model,
                    eff_area_model=m.eff_area_model,
                    datasets_names=dataset_read.name,
                )
            #for p in irf.parameters:
            #    p.frozen = False
            #    p.value = models_load.parameters[p.name].value
            #    p.error = models_load.parameters[p.name].error
            #    p.frozen = models_load.parameters[p.name].frozen

            models.append(irf)
    dataset_read.models = models
    return dataset_read


def load_dataset(dataset_empty, path):
    models_load = Models.read(path).copy()
    Source = models_load.names[0]
    models = Models(models_load[Source].copy())
    dataset_read = dataset_empty.copy()

    bkg = FoVBackgroundModel(dataset_name=dataset_read.name)
    for p in bkg.parameters:
        p.value = models_load.parameters[p.name].value
        p.error = models_load.parameters[p.name].error

    models.append(bkg)
    dataset_read.models = models
    return dataset_read
