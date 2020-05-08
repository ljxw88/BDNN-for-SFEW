import torch
from torch.autograd import Variable
import torch.nn.functional as F
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from torch.utils.data import Dataset,DataLoader,TensorDataset
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import confusion_matrix
from sklearn.preprocessing import LabelEncoder
# np.random.seed(5)

data = pd.read_excel('/Users/michael/Desktop/COMP4660/Assignment1/faces-emotion (images)/SFEW.xlsx')
data = data.fillna(0)
column_names = ['Name','Label','LPQ feature 1','LPQ feature 2','LPQ feature 3','LPQ feature 4','LPQ feature 5','PHOG feature 1','PHOG feature 2','PHOG feature 3','PHOG feature 4','PHOG feature 5']
data.columns = column_names
le = LabelEncoder()
data['Label'] = le.fit_transform(data['Label'])

feature_LPQ = ['LPQ feature 1','LPQ feature 2','LPQ feature 3','LPQ feature 4','LPQ feature 5']
feature_PHOG = ['PHOG feature 1','PHOG feature 2','PHOG feature 3','PHOG feature 4','PHOG feature 5']
feature_ALL = feature_LPQ + feature_PHOG
# display(data)
msk = np.random.rand(len(data)) < 0.8
scaler = StandardScaler()
scaler.fit(data[feature_ALL])
# print(scaler.mean_)
data[feature_ALL] = scaler.transform(data[feature_ALL])
train_data = data[msk].copy()
test_data = data[~msk].copy()
# print(len(train_data),len(test_data))

train_data_LPQ = train_data[feature_LPQ]
test_data_LPQ = test_data[feature_LPQ]

train_data_PHOG = train_data[feature_PHOG]
test_data_PHOG = test_data[feature_PHOG]

train_data_ALL = train_data[feature_LPQ+feature_PHOG]
test_data_ALL = test_data[feature_LPQ+feature_PHOG]

train_target = train_data['Label']
test_target = test_data['Label']

x_LPQ = torch.Tensor(train_data_LPQ.values).float()
x_PHOG = torch.Tensor(train_data_PHOG.values).float()
x_ALL = torch.Tensor(train_data_ALL.values).float()
y = torch.Tensor(train_target.values).long()
x_LPQ,y = Variable(x_LPQ),Variable(y)

test_x_LPQ = torch.Tensor(test_data_LPQ.values).float()
test_x_PHOG = torch.Tensor(test_data_PHOG.values).float()
test_x_ALL = torch.Tensor(test_data_ALL.values).float()
test_y = torch.Tensor(test_target.values).long()

class BiRNN(torch.nn.Module):
    def __init__(self, inputSize, hiddenSize, numLayers, numClasses):
        super(BiRNN, self).__init__()
        self.rnn = torch.nn.LSTM(
            input_size=inputSize,
            hidden_size=hiddenSize,
            num_layers=numLayers,
            batch_first=True,   # input & output: batch size -> first feature e.g. (batch, time_step, input_size)
            bidirectional=True,
        )
        self.out = torch.nn.Linear(hiddenSize * 2, numClasses)

    def forward(self, x):
        # x shape (batch, time_step, input_size)
        # r_out shape (batch, time_step, output_size)
        # h_n shape (n_layers, batch, hidden_size)
        # h_c shape (n_layers, batch, hidden_size)
        r_out, (h_n, h_c) = self.rnn(x, None)   # None -> hidden state are all 0 stat
        out = self.out(r_out[:, -1, :])
        return out

num_classes = 7
learning_rate = 0.02
hidden = 70
num_epochs = 300
batch_size = 64
time_step = 1
layer_size = 1

input = x_ALL
input_size = input.shape[1]
test_input = test_x_ALL
dataset_combine = TensorDataset(input,y)
train_loader = DataLoader(dataset = dataset_combine, batch_size=batch_size, shuffle=True, num_workers=2)

net = BiRNN(input_size, hidden, layer_size, num_classes)
print(net)

optimizer = torch.optim.Adam(net.parameters(), lr=learning_rate)
criterion = torch.nn.CrossEntropyLoss()

all_losses = []
all_accuracy = []
for epoch in range(num_epochs):
    for step,(x_,y_) in enumerate(train_loader):
        b_x = Variable(x_.view(-1,time_step,input_size))
        b_y = Variable(y_)
        output = net(b_x)
        loss = criterion(output,b_y)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

    test_out = net(input.view(-1,time_step,input_size))
    pred = torch.max(F.softmax(test_out,dim=0),1)[1].numpy()
    accuracy = sum(pred == y.numpy())/len(pred)
    all_losses.append(loss.item())
    all_accuracy.append(accuracy)
    if (epoch + 1) % 10 == 0:
        # test_out = net(input.view(-1,time_step,input_size))
        # pred = torch.max(F.softmax(test_out,dim=0),1)[1].numpy()
        # accuracy = sum(pred == y.numpy())/len(pred)
        print('Training Epoch: [%d/%d], Loss: %.4f, Accuracy: %.2f%%'
              % (epoch + 1, num_epochs, loss.item(), accuracy*100.))

test_out = net(test_input.view(-1,time_step,input_size))
pred = torch.max(F.softmax(test_out,dim=0),1)[1].numpy()
print('Testing Accuracy: %.2f%%'%(sum(pred == test_y.numpy())/len(pred)))

# new_list = []
# for i in range(len(all_losses)):
#     new_list.append([all_losses[i],all_accuracy[i]*100.])
# test=pd.DataFrame(columns=['lpqnn_loss','lpqnn_acc'],data=new_list)
# test.to_csv('./csv/lpqbrnn.csv')

fig = plt.figure(figsize=(8,3))
ax1 = fig.add_subplot(121)
ax2 = fig.add_subplot(122)
ax1.set_xlabel('epoch')
ax1.set_ylabel('training accuracy')
ax1.plot(all_accuracy)

ax2.set_xlabel('epoch')
ax2.set_ylabel('training loss')
ax2.plot(all_losses,color='b')
plt.show()
