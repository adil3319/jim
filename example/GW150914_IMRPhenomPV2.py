import time

import jax
import jax.numpy as jnp

from jimgw.jim import Jim
from jimgw.jim import Jim
from jimgw.prior import (
    CombinePrior,
    UniformPrior,
    CosinePrior,
    SinePrior,
    PowerLawPrior,
    UniformSpherePrior,
)
from jimgw.single_event.detector import H1, L1
from jimgw.single_event.likelihood import TransientLikelihoodFD
from jimgw.single_event.waveform import RippleIMRPhenomPv2
from jimgw.transforms import BoundToUnbound
from jimgw.single_event.transforms import (
    ComponentMassesToChirpMassSymmetricMassRatioTransform,
    SkyFrameToDetectorFrameSkyPositionTransform,
    ComponentMassesToChirpMassMassRatioTransform,
)
from jimgw.single_event.utils import Mc_q_to_m1_m2
from flowMC.strategy.optimization import optimization_Adam

jax.config.update("jax_enable_x64", True)

###########################################
########## First we grab data #############
###########################################

total_time_start = time.time()

# first, fetch a 4s segment centered on GW150914
gps = 1126259462.4
start = gps - 2
end = gps + 2
fmin = 20.0
fmax = 1024.0

ifos = ["H1", "L1"]

H1.load_data(gps, 2, 2, fmin, fmax, psd_pad=16, tukey_alpha=0.2)
L1.load_data(gps, 2, 2, fmin, fmax, psd_pad=16, tukey_alpha=0.2)

waveform = RippleIMRPhenomPv2(f_ref=20)

###########################################
########## Set up priors ##################
###########################################

prior = []

# Mass prior
M_c_min, M_c_max = 10.0, 80.0
eta_min, eta_max = 0.2, 0.25
Mc_prior = UniformPrior(M_c_min, M_c_max, parameter_names=["M_c"])
eta_prior = UniformPrior(eta_min, eta_max, parameter_names=["eta"])

prior = prior + [Mc_prior, eta_prior]

# Spin prior
theta_jn_prior = SinePrior(parameter_names=["theta_jn"])
phi_jl_prior = UniformPrior(0.0, 2 * jnp.pi, parameter_names=["phi_jl"])
theta_1_prior = SinePrior(parameter_names=["theta_1"])
theta_2_prior = SinePrior(parameter_names=["theta_2"])
phi_12_prior = UniformPrior(0.0, 2 * jnp.pi, parameter_names=["phi_12"])
a_1_prior = UniformPrior(0.0, 1.0, parameter_names=["a_1"])
a_2_prior = UniformPrior(0.0, 1.0, parameter_names=["a_2"])

prior = prior + [
    theta_jn_prior,
    phi_jl_prior,
    theta_1_prior,
    theta_2_prior,
    phi_12_prior,
    a_1_prior,
    a_2_prior,
]

# Extrinsic prior
dL_prior = PowerLawPrior(1.0, 2000.0, 2.0, parameter_names=["d_L"])
t_c_prior = UniformPrior(-0.05, 0.05, parameter_names=["t_c"])
phase_c_prior = UniformPrior(0.0, 2 * jnp.pi, parameter_names=["phase_c"])
iota_prior = SinePrior(parameter_names=["iota"])
psi_prior = UniformPrior(0.0, jnp.pi, parameter_names=["psi"])
ra_prior = UniformPrior(0.0, 2 * jnp.pi, parameter_names=["ra"])
dec_prior = CosinePrior(parameter_names=["dec"])

prior = prior + [
    dL_prior,
    t_c_prior,
    phase_c_prior,
    iota_prior,
    psi_prior,
    ra_prior,
    dec_prior,
]


prior = CombinePrior(prior)

likelihood = TransientLikelihoodFD(
    [H1, L1], waveform=waveform, trigger_time=gps, duration=4, post_trigger_duration=2
)


mass_matrix = jnp.eye(prior.n_dim)
mass_matrix = mass_matrix.at[1, 1].set(1e-3)
mass_matrix = mass_matrix.at[9, 9].set(1e-3)
local_sampler_arg = {"step_size": mass_matrix * 1e-3}

Adam_optimizer = optimization_Adam(n_steps=3000, learning_rate=0.01, noise_level=1)

# import optax

# n_epochs = 20
# n_loop_training = 100
# total_epochs = n_epochs * n_loop_training
# start = total_epochs // 10
# learning_rate = optax.polynomial_schedule(
#     1e-3, 1e-4, 4.0, total_epochs - start, transition_begin=start
# )

# jim = Jim(
#     likelihood,
#     prior,
#     n_loop_training=n_loop_training,
#     n_loop_production=20,
#     n_local_steps=10,
#     n_global_steps=1000,
#     n_chains=500,
#     n_epochs=n_epochs,
#     learning_rate=learning_rate,
#     n_max_examples=30000,
#     n_flow_sample=100000,
#     momentum=0.9,
#     batch_size=30000,
#     use_global=True,
#     keep_quantile=0.0,
#     train_thinning=1,
#     output_thinning=10,
#     local_sampler_arg=local_sampler_arg,
#     # strategies=[Adam_optimizer,"default"],
# )

# import numpy as np

# # chains = np.load('./GW150914_init.npz')['chain']

# jim.sample(jax.random.PRNGKey(42))  # ,initial_guess=chains)
