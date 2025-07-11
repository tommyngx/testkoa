import os
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import confusion_matrix, roc_curve, auc
import requests
from matplotlib import font_manager
#from scipy import interp
from numpy import interp
from sklearn.utils import resample

def save_confusion_matrix(labels, preds, class_names, output_dir, epoch=None, acc=None, filename_prefix="", custom_title=None):
    plt.style.use('default')
    
    # Download the font file if it does not exist
    font_url = 'https://github.com/tommyngx/style/blob/main/Poppins.ttf?raw=true'
    font_path = 'Poppins.ttf'
    if not os.path.exists(font_path):
        response = requests.get(font_url)
        with open(font_path, 'wb') as f:
            f.write(response.content)

    # Load the font
    font_manager.fontManager.addfont(font_path)
    prop = font_manager.FontProperties(fname=font_path)

    # Compute confusion matrix
    cm = confusion_matrix(labels, preds)
    
    # Normalize the confusion matrix
    cm_normalized = cm.astype("float") / cm.sum(axis=1)[:, np.newaxis]
    
    # Create an annotation matrix with both counts and percentages
    annot = np.empty_like(cm).astype(str)
    nrows, ncols = cm.shape
    for i in range(nrows):
        for j in range(ncols):
            count = cm[i, j]
            percent = cm_normalized[i, j] * 100
            annot[i, j] = f'{percent:.1f}%\n({count})'
    
    # Plot the heatmap
    plt.figure(figsize=(7, 6))
    ax = sns.heatmap(
        cm_normalized, 
        annot=annot, 
        fmt='', 
        cmap="Purples", 
        xticklabels=class_names, 
        yticklabels=class_names, 
        cbar=True,
        vmin=0, vmax=1,
        annot_kws={"fontsize": 14}  # Increase annotation font size here
    )
    # Customize the color bar
    ticks = np.linspace(0, 1, 5)  # Define ticks from 0 to 1
    cbar = ax.collections[0].colorbar  # Get the color bar from the current Axes
    cbar.set_ticks(ticks)  # Set specific ticks
    cbar.ax.set_yticklabels([f'{int(t * 100)}%' for t in ticks])    
    
    plt.xlabel("Predicted", fontproperties=prop, fontsize=18)  # Increase label font size
    plt.ylabel("Actual", fontproperties=prop, fontsize=18)
    # Use custom title if provided
    if custom_title is not None:
        title = custom_title
    else:
        title = "Confusion Matrix"
        if epoch is not None:
            title += f" - Epoch {epoch}"
    plt.title(title, fontproperties=prop, fontsize=20, pad=20)  # Increase title font size
    
    # Adjust layout to leave some space around the plot
    #plt.subplots_adjust(left=0.10, right=0.90, top=0.90, bottom=0.10)
    
    # Save the figure
    filename = f"{filename_prefix}confusion_matrix.png" if epoch is None else f"{filename_prefix}confusion_matrix_epoch_{epoch}_acc_{acc:.4f}.png"
    plt.savefig(os.path.join(output_dir, filename))
    plt.close()
    
    # Keep only the top 3 confusion matrices based on accuracy
    saved_files = sorted(
        [f for f in os.listdir(output_dir) if f.startswith("confusion_matrix_epoch_")],
        key=lambda x: float(x.split('_acc_')[-1].split('.png')[0]),
        reverse=True
    )
    for file in saved_files[3:]:
        os.remove(os.path.join(output_dir, file))

def save_roc_curve(labels, positive_risk, class_names, output_dir, epoch=None, acc=None, filename_prefix=""):
    # Apply ggplot style
    #plt.style.use('ggplot')
    plt.style.use('default')

    # Download the font file if it does not exist
    font_url = 'https://github.com/tommyngx/style/blob/main/Poppins.ttf?raw=true'
    font_path = 'Poppins.ttf'
    if not os.path.exists(font_path):
        response = requests.get(font_url)
        with open(font_path, 'wb') as f:
            f.write(response.content)

    # Load the font
    font_manager.fontManager.addfont(font_path)
    prop = font_manager.FontProperties(fname=font_path)

    # Binarize labels for disease detection
    labels = np.array(labels)
    labels = np.where(labels > 1, 1, 0)

    # Handle NaN values in labels and positive_risk
    mask = ~np.isnan(positive_risk) & ~np.isnan(labels)
    labels = labels[mask]
    positive_risk = positive_risk[mask]

    # Compute ROC curve safely
    if len(np.unique(labels)) < 2:
        print("Insufficient unique labels to compute ROC curve.")
        return

    # Plot ROC curve
    fpr, tpr, _ = roc_curve(labels, positive_risk, pos_label=1)
    roc_auc = auc(fpr, tpr)

    # Bootstrap for confidence interval
    bootstrapped_scores = []
    for i in range(1000):
        indices = resample(np.arange(len(labels)), replace=True)
        if len(np.unique(labels[indices])) < 2:
            continue
        score = auc(*roc_curve(labels[indices], positive_risk[indices])[:2])
        bootstrapped_scores.append(score)
    sorted_scores = np.array(bootstrapped_scores)
    sorted_scores.sort()
    confidence_lower = sorted_scores[int(0.025 * len(sorted_scores))]
    confidence_upper = sorted_scores[int(0.975 * len(sorted_scores))]

    plt.figure(figsize=(8, 7))
    plt.plot(fpr, tpr, color='darkred', lw=2, label=f'AUC: {roc_auc*100:.0f}% ({confidence_lower*100:.0f}% - {confidence_upper*100:.0f}%)')
    plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
    plt.xlim([-0.05, 1.05])
    plt.ylim([-0.05, 1.05])
    plt.xlabel('1 - Specificity', fontproperties=prop, fontsize=16)
    plt.ylabel('Sensitivity', fontproperties=prop, fontsize=16)
    plt.xticks(np.arange(0, 1.1, step=0.20), labels=[f'{int(x*100)}%' for x in np.arange(0, 1.1, step=0.20)], fontsize=15)
    plt.yticks(np.arange(0, 1.1, step=0.20), labels=[f'{int(y*100)}%' for y in np.arange(0, 1.1, step=0.20)], fontsize=15)
    title = 'Receiver Operating Characteristic'
    if epoch is not None:
        title += f" - Epoch {epoch}"
    plt.title(title, fontproperties=prop, fontsize=18, pad=20)
    
    # Customize legend
    legend = plt.legend(loc="lower right", prop={'size': 16, 'family': prop.get_name()})
    legend.get_frame().set_facecolor('white')
    legend.get_frame().set_edgecolor('black')

    fig = plt.gcf()
    fig.patch.set_facecolor('white')  # Set the background color outside the plot area to white
    #plt.gca().set_facecolor('white')  # Set the background color inside the plot area to white
    plt.subplots_adjust(left=0.15, right=0.90, top=0.9, bottom=0.10)
    filename = f"{filename_prefix}roc_curve.png" if epoch is None else f"{filename_prefix}roc_curve_epoch_{epoch}_acc_{acc:.4f}.png"
    plt.savefig(os.path.join(output_dir, filename))
    plt.close()
    
    # Keep only the best top 3 ROC curves based on accuracy
    saved_files = sorted([f for f in os.listdir(output_dir) if f.startswith("roc_curve_epoch_")], key=lambda x: float(x.split('_acc_')[-1].split('.png')[0]), reverse=True)
    for file in saved_files[3:]:
        os.remove(os.path.join(output_dir, file))

def tr_plot(tr_data, start_epoch, output_dir):
    # Plot the training and validation data
    tacc = tr_data['accuracy']
    tloss = tr_data['loss']
    vacc = tr_data['val_accuracy']
    vloss = tr_data['val_loss']
    Epoch_count = len(tacc)
    Epochs = list(range(start_epoch + 1, start_epoch + Epoch_count + 1))
    index_loss = np.argmin(vloss)  # this is the epoch with the lowest validation loss
    val_lowest = vloss[index_loss]
    index_acc = np.argmax(vacc)
    acc_highest = vacc[index_acc]
    plt.style.use('fivethirtyeight')
    sc_label = 'best epoch= ' + str(index_loss + 1 + start_epoch)
    vc_label = 'best epoch= ' + str(index_acc + 1 + start_epoch)
    fig, axes = plt.subplots(nrows=1, ncols=2, figsize=(20, 8))
    axes[0].plot(Epochs, tloss, 'r', label='Training loss')
    axes[0].plot(Epochs, vloss, 'g', label='Validation loss')
    axes[0].scatter(index_loss + 1 + start_epoch, val_lowest, s=150, c='blue', label=sc_label)
    axes[0].set_title('Training and Validation Loss')
    axes[0].set_xlabel('Epochs')
    axes[0].set_ylabel('Loss')
    legend = axes[0].legend()
    legend.get_frame().set_facecolor('white')
    legend.get_frame().set_edgecolor('black')
    axes[1].plot(Epochs, tacc, 'r', label='Training Accuracy')
    axes[1].plot(Epochs, vacc, 'g', label='Validation Accuracy')
    axes[1].scatter(index_acc + 1 + start_epoch, acc_highest, s=150, c='blue', label=vc_label)
    axes[1].set_title('Training and Validation Accuracy')
    axes[1].set_xlabel('Epochs')
    axes[1].set_ylabel('Accuracy')
    legend = axes[1].legend()
    legend.get_frame().set_facecolor('white')
    legend.get_frame().set_edgecolor('black')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir,'logs', f"training_plot.png"))
    plt.close()