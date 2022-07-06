from sas.core.sas_core import SAS
from mishra_bird import mishra_bird
import numpy as np
from matplotlib import pyplot as plt
from matplotlib import cm

@np.vectorize
def predict_sur_sample(surrogate, x, y):
    sample ={'/dataSchema/x': x,
             '/dataSchema/y': y}

    output = surrogate.predict(sample)
    return output['/dataSchema/f']

@np.vectorize
def predict_sur_variance(surrogate, x, y):

    output = surrogate.surrogate.predict_variances(np.array([x, y]).reshape((1, -1)))
    return output[0]

def calculate_RMSE(surrogate, x_limits, y_limits, resolution=200):
    x_range = np.linspace(x_limits[0], x_limits[1], resolution)
    y_range = np.linspace(y_limits[0], y_limits[1], resolution)

    X, Y = np.meshgrid(x_range, y_range)
    F = mishra_bird(X, Y)
    sur_prediction = predict_sur_sample(surrogate, X, Y)

    prediction_error = F - sur_prediction
    RMSE = np.square(prediction_error)
    RMSE = np.sqrt(np.mean(prediction_error ** 2))

    return RMSE

def plot_mishra(surrogate, x_limits, y_limits, resolution):
    x_range = np.linspace(x_limits[0], x_limits[1], resolution)
    y_range = np.linspace(y_limits[0], y_limits[1], resolution)

    X, Y = np.meshgrid(x_range, y_range)
    F = mishra_bird(X, Y)

    size = resolution**2

    sur_variances = predict_sur_variance(surrogate, X, Y)
    sur_prediction = predict_sur_sample(surrogate, X, Y)


    new_point = surrogate.propose_new_sample()
    x_new = new_point['/dataSchema/x']
    y_new = new_point['/dataSchema/y']

    prediction_error = F-sur_prediction
    RMSE = np.sqrt(np.sum(prediction_error ** 2) / size)

    fig, (ax1, ax2, ax3, ax4) = plt.subplots(1, 4)
    fullF = ax1.contourf(X, Y, F, 100, cmap=cm.coolwarm)
    fullC = ax1.contour(X, Y, F, colors='white')
    points = ax1.plot(surrogate.all_input_samples[:, 0], surrogate.all_input_samples[:, 1], 'r*', label='Sample Points')
    new_point = ax1.plot(x_new, y_new, 'b*', label='New Point')

    surF = ax2.contourf(X, Y, sur_prediction, 100, cmap=cm.coolwarm)
    surC = ax2.contour(X, Y, sur_prediction, colors='white')
    points = ax2.plot(surrogate.all_input_samples[:, 0], surrogate.all_input_samples[:, 1], 'r*', label='Sample Points')
    new_point = ax2.plot(x_new, y_new, 'b*', label='New Point')

    errorF = ax3.contourf(X, Y, np.abs(prediction_error), 100, cmap=cm.Reds)
    errorC = ax3.contour(X, Y, np.abs(prediction_error), colors='white')
    points = ax3.plot(surrogate.all_input_samples[:, 0], surrogate.all_input_samples[:, 1], 'r*', label='Sample Points')
    new_point = ax3.plot(x_new, y_new, 'b*', label='New Point')

    varF = ax4.contourf(X, Y, sur_variances, 1000, cmap=cm.Reds)
    varC = ax4.contour(X, Y, sur_variances, colors='white')
    points = ax4.plot(surrogate.all_input_samples[:, 0], surrogate.all_input_samples[:, 1], 'r*', label='Sample Points')
    new_point = ax4.plot(x_new, y_new, 'b*', label='New Point')

    fig.colorbar(fullF, ax=ax1)  # Add a colorbar to a plot
    fig.colorbar(surF, ax=ax2)  # Add a colorbar to a plot
    fig.colorbar(errorF, ax=ax3)  # Add a colorbar to a plot
    fig.colorbar(varF, ax=ax4)  # Add a colorbar to a plot

    ax1.title.set_text('Analytical')
    ax1.set_xlabel('x')
    ax1.set_ylabel('y')
    ax2.title.set_text('Surrogate Prediction')
    ax2.set_xlabel('x')
    ax2.set_ylabel('y')
    ax3.title.set_text(f'Error (RMSE={RMSE:.2f})')
    ax3.set_xlabel('x')
    ax3.set_ylabel('y')

    plt.show()
    print('Stop')


def main():
    sas = SAS(cmdows_opt_file='CMDOWS/MDG-unconverged-OPT.xml',
              cmdows_fpg_file='CMDOWS/FPG-unconverged-OPT.xml',
              initial_cpacs='mishra_bird-input.xml')

    sas.init_pido()
    x_limits = [-10, 0]
    y_limits = [-10, 0]


    sas.deploy_all_disciplines(
        tool_folder=r"C:\Dev\Thesis\surrogateassistancesystem\tool_repository\math_test_problems",
        overwrite=True)

    disciplines = 'mishra_bird'

    doe_wf = r"C:\Users\Costijn\.rce\default\workspace\Mishra\mishra_bird_DoE.wf"
    opt_wf = r"C:\Users\Costijn\.rce\default\workspace\Mishra\Mishra.wf"

    surrogate_options = dict(mode='fixed_type',
                             model_type='KRG',
                             training_set='validated')

    surrogate_options = dict(mode='automatic',
                             selection='all',
                             training_set='validated')

    sas.build_doe_for_disciplines(disciplines=disciplines)

    n_samples = 20
    sampling_plan = sas.generate_samples(n_samples=n_samples, disciplines=disciplines,
                                         custom_range={'/dataSchema/x': x_limits,
                                                       '/dataSchema/y': y_limits},
                                         seed=1)

    doe_wf_sampled = sas.deploy_samples_into_workflow(wf_file=doe_wf, sampling_plan=sampling_plan)
    run_id = sas.run_pido(wf_file=doe_wf_sampled)



    sm_key = sas.init_surrogate_model(disciplines=disciplines)
    surrogate = sas.surrogate_models[sm_key]
    surrogate.validation_metric = 'RMSE'

    sas.build_surrogate_model(disciplines=disciplines, **surrogate_options)
    RMSE = calculate_RMSE(surrogate, x_limits, y_limits)

    errors = [surrogate.error]
    errors_exact = [calculate_RMSE(surrogate, x_limits, y_limits)]

    sample_max = 50
    sample_range = range(n_samples+1, sample_max+1)
    selected_samples = []
    for n_sample in sample_range:
        print(n_sample)
        sas.database.delete_run(run_id)
        sampling_plan = sas.generate_samples(n_samples=n_sample, disciplines=disciplines,
                                             custom_range={'/dataSchema/x': x_limits,
                                                           '/dataSchema/y': y_limits},
                                             seed=1)

        doe_wf_sampled = sas.deploy_samples_into_workflow(wf_file=doe_wf, sampling_plan=sampling_plan)
        run_id = sas.run_pido(wf_file=doe_wf_sampled)
        sas.build_surrogate_model(disciplines=disciplines, **surrogate_options)
        errors.append(surrogate.error)
        errors_exact.append(calculate_RMSE(surrogate, x_limits, y_limits))
    plot_mishra(sas.surrogate_models[sm_key], x_limits, y_limits, 200)

if __name__ == '__main__':
    main()
