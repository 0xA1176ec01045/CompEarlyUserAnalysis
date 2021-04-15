import pandas as pd
import matplotlib.pyplot as plt
from math import log10

plt.figure(figsize=(8,4))

ProposalData = pd.read_csv('Proposal.50-50.csv', sep=r"\s*", names=['address','COMP'])
fig = plt.hist(ProposalData['COMP'],bins=100)

plt.title('Proposed Distribution of COMP: 50% socially-weighted, 50% capital-weighted')
plt.yscale('log')
plt.xlabel('COMP per address')
plt.ylabel('Number of addresses')
plt.savefig('Proposal.50-50.png')
