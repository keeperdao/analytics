# ROOK Tokenomics

## Introduction

- Introduce need for tokenomics modeling
- Lots of discussion in discord, etc about various components of our tokenomics
- High level overview of this project
- Stress none of this is final, and it's meant to open the discussion

## Methodology

This will be a high level overview of the thought process behind designing these models. It will not dig into the math or implementation, that will be handled in the individual pages for each model. Instead it will provide a summary of the various parameters included in the models with some rationale.

- Considerations
  - Modeling mainly what we can control directly (i.e. protocol params, ecosystem params, etc and NOT external buy/sell pressures)
  - Attempts to strike balance between ease of implementation and accuracy (i.e. using constant product AMM for liquidity)
- Coordination Protocol params (what we have direct, absolute control of)
  - Bidding Parameters:
    - Bid token (ETH vs ROOK)
    - Target Bid % (what % of expected MEV profit do keepers bid)
      - Treat greenlight algo as black box that works to achieve desired target bid %, modeling the greenlight algo is out of scope
  - Bid distribution parameters:
    - Treasury %
    - Partner %
    - Staking %
    - Burn %
    - User % (100% - all the above, i.e. what's left over)
  - Staking parameters:
    - staking-based user rewards % (reward % increases with amount staked)
    - staking lockup period?
- Ecosystem Parameters (we have varying levels of control indirectly, but not absolute)
  - MEV to Volume ratio
  - ROOK liquidity modeling (constant product AMM):
    - Constant liquidity in USD
    - Liquidity as a % of USD market cap
    - Liquidity as a % of ROOK circulating supply
  - Volume modeling:
    - Constant daily volume
    - Linear volume growth
    - Logistic volume growth
  - User and partner rewards claim (and dump) %
- DAO Parameters
  - Treasury burn rate in USD (for contributor salaries and other expenses)
