"""Proximal Policy Optimization for RL2."""
from garage.torch.algos import RL2
import torch
from garage.torch.optimizers import OptimizerWrapper, WarmupOptimizerWrapper, LRDecayOptimizerWrapper
from garage.torch import global_device


class RL2PPO(RL2):
    """Proximal Policy Optimization specific for RL^2.

    See https://arxiv.org/abs/1707.06347 for algorithm reference.

    Args:
        meta_batch_size (int): Meta batch size.
        task_sampler (TaskSampler): Task sampler.
        env_spec (EnvSpec): Environment specification.
        policy (garage.tf.policies.StochasticPolicy): Policy.
        baseline (garage.tf.baselines.Baseline): The baseline.
        episodes_per_trial (int): Used to calculate the max episode length for
            the inner algorithm.
        scope (str): Scope for identifying the algorithm.
            Must be specified if running multiple algorithms
            simultaneously, each using different environments
            and policies.
        discount (float): Discount.
        gae_lambda (float): Lambda used for generalized advantage
            estimation.
        center_adv (bool): Whether to rescale the advantages
            so that they have mean 0 and standard deviation 1.
        positive_adv (bool): Whether to shift the advantages
            so that they are always positive. When used in
            conjunction with center_adv the advantages will be
            standardized before shifting.
        fixed_horizon (bool): Whether to fix horizon.
        lr_clip_range (float): The limit on the likelihood ratio between
            policies, as in PPO.
        max_kl_step (float): The maximum KL divergence between old and new
            policies, as in TRPO.
        optimizer_args (dict): The arguments of the optimizer.
        policy_ent_coeff (float): The coefficient of the policy entropy.
            Setting it to zero would mean no entropy regularization.
        use_softplus_entropy (bool): Whether to estimate the softmax
            distribution of the entropy to prevent the entropy from being
            negative.
        use_neg_logli_entropy (bool): Whether to estimate the entropy as the
            negative log likelihood of the action.
        stop_entropy_gradient (bool): Whether to stop the entropy gradient.
        entropy_method (str): A string from: 'max', 'regularized',
            'no_entropy'. The type of entropy method to use. 'max' adds the
            dense entropy to the reward for each time step. 'regularized' adds
            the mean entropy to the surrogate objective. See
            https://arxiv.org/abs/1805.00909 for more details.
        meta_evaluator (garage.experiment.MetaEvaluator): Evaluator for meta-RL
            algorithms.
        n_epochs_per_eval (int): If meta_evaluator is passed, meta-evaluation
            will be performed every `n_epochs_per_eval` epochs.
        name (str): The name of the algorithm.

    """

    def __init__(self,
                 meta_batch_size,
                 task_sampler,
                 env_spec,
                 policy,
                 value_function,
                 episodes_per_trial,
                 steps_per_epoch,
                 n_epochs,
                 policy_lr=2.5e-4,
                 vf_lr=2.5e-4,
                 policy_lr_schedule="default",
                 vf_lr_schedule="default",
                 max_opt_epochs=10,
                 minibatch_size=64,
                 vf_optimizer=None,
                 discount=0.99,
                 gae_lambda=1,
                 center_adv=True,
                 positive_adv=False,
                 lr_clip_range=0.01,
                 optimizer_args=None,
                 policy_ent_coeff=0.0,
                 use_softplus_entropy=False,
                 stop_entropy_gradient=False,
                 entropy_method='no_entropy',
                 meta_evaluator=None,
                 n_epochs_per_eval=10,
                 decay_epoch_init=500,
                 decay_epoch_end=1000,
                 min_lr_factor=0.1,
                 name='PPO'):
        if optimizer_args is None:
            optimizer_args = dict()
        
        if policy_lr_schedule == "warmup":
            policy_optimizer = WarmupOptimizerWrapper(
                (torch.optim.AdamW, dict(lr=policy_lr)),
                policy,
                max_optimization_epochs=max_opt_epochs,
                minibatch_size=minibatch_size,
                steps_per_epoch=steps_per_epoch,
                n_epochs=n_epochs
            )
        elif policy_lr_schedule == "decay":
            policy_optimizer = LRDecayOptimizerWrapper(
                (torch.optim.AdamW, dict(lr=policy_lr)),
                policy,
                max_optimization_epochs=max_opt_epochs,
                minibatch_size=minibatch_size,
                steps_per_epoch=steps_per_epoch,
                n_epochs=n_epochs,
                decay_epoch_init=decay_epoch_init,
                decay_epoch_end=decay_epoch_end,
                min_lr_factor=min_lr_factor
            )
        elif policy_lr_schedule == "no_schedule":
            policy_optimizer = OptimizerWrapper(
                (torch.optim.AdamW, dict(lr=policy_lr)),
                policy,
                max_optimization_epochs=max_opt_epochs,
                minibatch_size=minibatch_size)
        else:
            raise NotImplementedError

        if vf_lr_schedule == "warmup":
            vf_optimizer = WarmupOptimizerWrapper(
                (torch.optim.AdamW, dict(lr=vf_lr)),
                value_function,
                max_optimization_epochs=max_opt_epochs,
                minibatch_size=minibatch_size,
                steps_per_epoch=steps_per_epoch,
                n_epochs=n_epochs
            )
        elif vf_lr_schedule == "decay":
            vf_optimizer = LRDecayOptimizerWrapper(
                (torch.optim.AdamW, dict(lr=vf_lr)),
                value_function,
                max_optimization_epochs=max_opt_epochs,
                minibatch_size=minibatch_size,
                steps_per_epoch=steps_per_epoch,
                n_epochs=n_epochs,
                decay_epoch_init=decay_epoch_init,
                decay_epoch_end=decay_epoch_end,
                min_lr_factor=min_lr_factor
            )
        elif vf_lr_schedule == "no_schedule":
            vf_optimizer = OptimizerWrapper(
                (torch.optim.AdamW, dict(lr=vf_lr)),
                value_function,
                max_optimization_epochs=max_opt_epochs,
                minibatch_size=minibatch_size)
        else:
            raise NotImplementedError

        super().__init__(meta_batch_size=meta_batch_size,
                         task_sampler=task_sampler,
                         env_spec=env_spec,
                         policy=policy,
                         value_function=value_function,
                         policy_optimizer=policy_optimizer,
                         vf_optimizer=vf_optimizer,
                         lr_clip_range=lr_clip_range,
                         episodes_per_trial=episodes_per_trial,
                         discount=discount,
                         gae_lambda=gae_lambda,
                         center_adv=center_adv,
                         positive_adv=positive_adv,
                         policy_ent_coeff=policy_ent_coeff,
                         use_softplus_entropy=use_softplus_entropy,
                         stop_entropy_gradient=stop_entropy_gradient,
                         entropy_method=entropy_method,
                         meta_evaluator=meta_evaluator,
                         n_epochs_per_eval=n_epochs_per_eval)

    @property
    def networks(self):
        """Return all the networks within the model.

        Returns:
            list: A list of networks.

        """
        return [
            self.policy, self.value_function, self.old_policy
        ]

    def to(self, device=None):
        """Put all the networks within the model on device.

        Args:
            device (str): ID of GPU or CPU.

        """
        device = device or global_device()
        for net in self.networks:
            net.to(device)