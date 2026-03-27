# Connecting Measured BRDFs to Analytic BRDFs by Data-Driven Diffuse-Specular Separation

TIANCHENG SUN, University of California, San Diego
HENRIK WANN JENSEN, University of California, San Diego
RAVI RAMAMOORTHI, University of California, San Diego

<span id="page-0-0"></span>![](_page_0_Figure_2.jpeg)

Fig. 1. We present a new framework for connecting measured and analytic BRDFs. In our method, (a) we first develop a robust diffuse-specular separation algorithm on measured BRDFs. This separation equips measured BRDFs with the flexibility and compactness of analytic models: (b) we are allowed to edit the diffuse and specular parts of the measured BRDFs separately, and (c) the measured BRDF can be expressed using only 8 parameters, which is the same number as for commonly used analytic BRDFs, such as the GGX model. (d) We further develop a robust and efficient algorithm to directly fit complex data-driven reflectances to two-lobe analytic materials, and our results outperform the traditional non-convex optimization in accuracy, speed, and stability.

The bidirectional reflectance distribution function (BRDF) is crucial for modeling the appearance of real-world materials. In production rendering, analytic BRDF models are often used to approximate the surface appearance since they are compact and flexible. Measured BRDFs usually have a more realistic appearance, but consume much more storage and are hard to modify. In this paper, we propose a novel framework for connecting measured and analytic BRDFs. First, we develop a robust method for separating a measured BRDF into diffuse and specular components. This is commonly done in analytic models, but has been difficult previously to do explicitly for measured BRDFs. This diffuse-specular separation allows novel measured BRDF editing on the diffuse and specular parts separately. In addition, we conduct analysis on each part of the measured BRDF, and demonstrate a more intuitive and lower-dimensional PCA model than Nielsen et al. [\[2015\]](#page-14-0). In fact, our measured BRDF model has the same number of parameters (8 parameters) as the commonly used analytic models, such as the GGX model. Finally, we visualize the analytic and measured BRDFs in the same space, and directly demonstrate their similarities and differences. We also design an analytic fitting algorithm for two-lobe materials, which is more robust, efficient and simple, compared to previous non-convex optimization-based analytic fitting methods.

Authors’ addresses: Tiancheng Sun, tis037@cs.ucsd.edu, University of California, San Diego; Henrik Wann Jensen, henrik@cs.ucsd.edu, University of California, San Diego; Ravi Ramamoorthi, ravir@cs.ucsd.edu, University of California, San Diego.

Permission to make digital or hard copies of all or part of this work for personal or classroom use is granted without fee provided that copies are not made or distributed for profit or commercial advantage and that copies bear this notice and the full citation on the first page. Copyrights for components of this work owned by others than the author(s) must be honored. Abstracting with credit is permitted. To copy otherwise, or republish, to post on servers or to redistribute to lists, requires prior specific permission and/or a fee. Request permissions from permissions@acm.org.

© 2018 Copyright held by the owner/author(s). Publication rights licensed to the Association for Computing Machinery.

0730-0301/2018/11-ART273 \$15.00 <https://doi.org/10.1145/3272127.3275026>
CCS Concepts: • Computing methodologies → Computer graphics; Reflectance modeling; Modeling methodologies;

Additional Key Words and Phrases: Measured BRDF models, Analytic BRDF models, Measured BRDF editing, Analytic BRDF fitting.

#### ACM Reference Format:

Tiancheng Sun, Henrik Wann Jensen, and Ravi Ramamoorthi. 2018. Connecting Measured BRDFs to Analytic BRDFs by Data-Driven Diffuse-Specular Separation. ACM Trans. Graph. 37, 6, Article 273 (November 2018), [15](#page-14-1) pages. <https://doi.org/10.1145/3272127.3275026>

# 1 INTRODUCTION

The wide variety of real-world surface appearances are usually represented by the bidirectional reflectance distribution function (BRDF) [\[Nicodemus et al.](#page-14-2) [1977\]](#page-14-2) in computer graphics. The BRDF, which describes how much light from an incoming direction is reflected to an outgoing direction, is a 4D function and can be reduced to 3D by assuming the material to be isotropic. Analytic BRDF models, which approximate the surface reflectance with a few parameters, are flexible, and are often used in production. On the other hand, measured BRDFs, such as the MERL dataset [\[Matusik et al.](#page-14-3) [2003a\]](#page-14-3), are by definition more accurate, but can involve significant complexity of measurement and storage, and can be difficult to edit or manipulate. To address these challenges, in this paper we equip the measured BRDFs with multiple properties of analytic BRDFs, explore the relation between analytic and measured BRDFs, and develop a robust and efficient way to fit analytic BRDFs to measured ones. Specifically, we make the following contributions:

Diffuse-Specular Separation. In Sec. [3,](#page-1-0) we introduce a novel 3-step optimization algorithm (Figs. [1a](#page-0-0) and [2\)](#page-2-0) to separate a measured

BRDF into a diffuse and a specular part, each with a color. While this separation has been trivial for analytic BRDFs, it has been very difficult previously for measured data. The separation gives measured BRDFs the form of analytic models, which makes the measured BRDFs more flexible and compact. We demonstrate three applications of this separation in Secs. [4-](#page-5-0)[6.](#page-9-0)

Measured BRDF Editing. In Sec. [4,](#page-5-0) we demonstrate several edits on measured BRDFs which benefit from separating the diffuse and specular parts. These edits (Figs. [1b](#page-0-0) and [9\)](#page-6-0) are straightforward on analytic BRDF models, but have previously not been easy to accomplish for measured BRDF models.

Compact Measured BRDF Model. In Sec. [5,](#page-6-1) we conduct principal component analyses on the separation results of BRDFs in the MERL dataset, and show that we can efficiently represent the diffuse part with 1 principal component in linear space, and the specular part with 3 principal components in logarithm space (Fig. [1c](#page-0-0)). This is more compact than the 5-dimensional subspace introduced by Nielsen et al. [\[2015\]](#page-14-0), which had the diffuse and specular parts mixed together in the principal components. More important, this is the first method to express measured BRDFs with the same number of parameters (8 parameters: 1 for diffuse, 3 for specular, and each part has 2 more for hue and saturation) as popular analytic models such as Lambertian plus GGX model [\[Walter et al. 2007\]](#page-14-4).

Relating and Fitting to Analytic BRDFs. In Sec. [6,](#page-9-0) we investigate the relations between the specular part of measured BRDFs and the GGX model. We visualize the analytic and measured BRDFs in the same low-dimensional principal component space (Fig. [17\)](#page-10-0), and show that the analytic BRDFs lie in a manifold in this space. We then develop an algorithm for fitting complex measured BRDFs to two-lobe analytic BRDFs. Compared to traditional non-convex optimization methods, our algorithm can yield a more accurate result in a much more robust and efficient way (Fig. [1d](#page-0-0)).

# 2 RELATED WORK

Analytic BRDF Models. Analytic BRDF models usually consist of a diffuse and a specular model, each with a color. The Lambertian model is widely used as the diffuse model, and there also exists a more precise model [\[Oren and Nayar 1995\]](#page-14-5). The specular behavior of the materials is much more complicated. Early models were mainly derived emprically [\[Phong 1975;](#page-14-6) [Blinn 1977;](#page-14-7) [Lafortune et al.](#page-14-8) [1997\]](#page-14-8). More recently, physically-based microfacet models were introduced [\[Cook and Torrance 1982;](#page-14-9) [Ward 1992;](#page-14-10) [Ashikmin et al. 2000\]](#page-14-11). Among these, the GGX model is currently widely used in production [\[Walter et al.](#page-14-4) [2007\]](#page-14-4). In our paper, we based our analysis on the Lambertian and GGX models.

Data-driven BRDFs. BRDF measurements from real-world materials are needed to validate analytic models. Matusik et al. [\[2003a\]](#page-14-3) constructed the first large-scale BRDF dataset, the MERL dataset, which contains 100 real-world materials covering a wide range of appearances. Each material consists of measurements from a dense set of directions. This dataset led to better understanding of realistic materials [\[McAuley et al.](#page-14-12) [2012;](#page-14-12) [Zubiaga et al.](#page-14-13) [2015;](#page-14-13) [Havran](#page-14-14)

[and Sbert 2015\]](#page-14-14), and inspired researchers to formulate more precise analytic models to match the measurements [\[Löw et al.](#page-14-15) [2012;](#page-14-15) [Bagher et al.](#page-14-16) [2012;](#page-14-16) [Brady et al.](#page-14-17) [2014;](#page-14-17) [Bagher et al.](#page-14-18) [2016\]](#page-14-18). By considering diffraction and the error introduced by acquisition apparatus, Holzschuch et al. [\[2017\]](#page-14-19) provided a very good approximation to measured BRDFs. There also exist other measured BRDF datasets such as UTIA [\[Filip and Vávra 2014\]](#page-14-20). However, the BRDFs in the UTIA dataset are mostly anisotropic and are sparsely sampled. For a comprehensive review on BRDF representation, please see the survey [\[Guarnera et al.](#page-14-21) [2016\]](#page-14-21). In our paper, we focus only on isotropic BRDFs in the MERL dataset. Rather than propose a more accurate model for the BRDF, we compress the measured BRDFs to the size of the analytic ones. We then reveal the relation between the analytic and measured BRDFs with this compact representation, and analyze the similarity and differences between them.

BRDF Decomposition. Several BRDF decomposition methods have been proposed to simplify the structure of measured BRDFs, including non-negative matrix factorization [\[Lawrence et al.](#page-14-22) [2004,](#page-14-22) [2006\]](#page-14-23), gaussian mixture [\[Sun et al.](#page-14-24) [2007\]](#page-14-24), and tensor decomposition [\[Bilgili](#page-14-25) [et al.](#page-14-25) [2011\]](#page-14-25). These methods implicitly did a diffuse-specular separation, but their assumption on each part is usually handcrafted and does not always hold. Soler et al. [\[2018\]](#page-14-26) proposed to embed the measured BRDFs in a compact manifold. While the representation has only two dimensions, their model has little physical meaning. In this paper, we infer the concept of diffuse and specular from analytic models. Recently, Nielsen et al. [\[2015\]](#page-14-0) expressed a measured BRDF with 5 principal components after a log-relative mapping. This method further compressed the size of the measured BRDF, but the color and different types of reflectances are all mixed together in the principal components. In our paper, we first separate the colors and the reflectances with a diffuse-specular separation, then do a similar log-relative mapping and principal component analysis only on our specular parts. By doing this, we obtain a more compact measured BRDF model than the model from Nielsen et al.

BRDF Fitting. BRDF fitting has been an open problem for decades. Ngan et al. [\[2005\]](#page-14-27) first did the fitting on the MERL dataset using the weighted <sup>L</sup><sup>2</sup> metric, and later there was more study on the choice of a good BRDF metric [\[Fores et al.](#page-14-28) [2012;](#page-14-28) [Löw et al.](#page-14-15) [2012;](#page-14-15) [Bagher et al.](#page-14-16) [2012;](#page-14-16) [Brady et al.](#page-14-17) [2014;](#page-14-17) [Bagher et al.](#page-14-18) [2016\]](#page-14-18). However, all these methods suffer from the local minima of non-convex optimization. Dupuy et al. [\[2015\]](#page-14-29) proposed an iterative method to extract the microfacet parameters from anisotropic materials, but only backscattering samples are used. In this paper, we propose a fitting algorithm that does an efficient search on the whole analytic gamut. The algorithm can produce accurate reconstruction results in a more robust and efficient way with no extra parameters.

# <span id="page-1-0"></span>3 DIFFUSE-SPECULAR SEPARATION

A measured BRDF accurately models the appearance of a real-world material, but its huge data size and high complexity have hindered practical adoption. In order to enhance their flexibility and compactness, we propose to separate measured BRDFs into diffuse and specular parts, each with a single color:

<span id="page-1-1"></span>
$$\rho(\omega_{i}, \omega_{o}, \lambda) \approx \rho_{d}(\omega_{i}, \omega_{o}) \cdot \mathbf{c}_{d}(\lambda) + \rho_{s}(\omega_{i}, \omega_{o}) \cdot \mathbf{c}_{s}(\lambda). \tag{1}$$

<span id="page-2-0"></span>![](_page_2_Figure_2.jpeg)

Fig. 2. An overview of our diffuse-specular separation algorithm using 3-step optimization. We first fit an analytic BRDF to the achromatic reflectance (average reflectance across color channels) of the target measured BRDF. Then, we use the analytic BRDF as guidance to separate the diffuse and specular parts of the measured BRDF. Finally, we restore the colors for each part. Note that since we render the BRDFs under a full environment map, the images may have some color even though the BRDFs are achromatic in steps 1 and 2.

The original measured BRDF $\rho$ is a function of incoming and outgoing light directions $\omega_i, \omega_o$ with wavelength $\lambda$ . $\rho_d, \rho_s$ are both single-channel reflectances, and $c_d$ , $c_s$ are RGB colors normalized to have the average value 1. This separation has decoupled colors and reflectances, as well as diffuse and specular parts, which enables simple editing on measured BRDFs (Sec. 4), a more compact measured BRDF model (Sec. 5), and more straightforward relation to analytic models (Sec. 6).

### 3.1 Separation Algorithm

The goal of the algorithm is to solve for the diffuse and specular measured BRDFs $\rho_d$ , $\rho_s$ as well as the corresponding colors $c_d$ , $c_s$ in Equ. 1. This is a highly nontrivial task: First, there don't exist strict definitions for diffuse and specular. In addition, the large variation of BRDF values makes the separation even harder. Given these challenges, we propose a 3-step optimization algorithm using analytic BRDFs as guidance for the separation. As shown in Fig. 2, we first approximate the achromatic shape of a measured BRDF with analytic models, and then in the second step we refine the result of the first step in order to exactly fit the target measured BRDF. At last, we restore the colors for both diffuse and specular parts of the measured BRDF.

We test our algorithm using the measured BRDFs from the MERL dataset [Matusik et al. 2003a]. This dataset contains 100 isotropic BRDFs captured from real world materials. Each BRDF is represented by $p = (180 \times 90 \times 90)$ measurements under Rusinkiewicz coordinates $(\phi_d, \theta_h, \theta_d)$ [Rusinkiewicz 1998]. For the analytic model, used as the initial approximation, we use the Lambertian model for diffuse and the GGX [Walter et al. 2007] model for specular. The expression for the specular GGX model we use is as follows:

<span id="page-2-3"></span>
$$\rho = \rho_{0} \cdot \frac{F(\omega_{i} \cdot h) \cdot D(\mathbf{n} \cdot h) \cdot G(\mathbf{n} \cdot \omega_{i}) G(\mathbf{n} \cdot \omega_{o})}{4(\mathbf{n} \cdot \omega_{i}) \cdot (\mathbf{n} \cdot \omega_{o})}$$

$$F(x) = \frac{1}{2} \left(\frac{g - x}{g + x}\right)^{2} \left(1 + \left(\frac{x(g + x) - 1}{x(g - x) + 1}\right)^{2}\right), g = \sqrt{n^{2} - 1 + x^{2}}$$

$$D(x) = \frac{m^{2}}{\pi \left[x^{2}(m^{2} - 1) + 1\right]^{2}}, G(x) = \frac{2}{1 + \sqrt{1 + m^{2} \cdot \frac{1 - x^{2}}{x^{2}}}},$$
(2)

where h is the half angle vector of $\omega_i$ and $\omega_o$ . $\rho_0$ , m, and n are the intensity, roughness, and index of refraction (IOR) of the analytic

In this section, we express both measured BRDFs $\rho$ and analytic BRDFs $\rho(\alpha)$ in the sampled form of the MERL dataset, where $\alpha$ represents the analytic parameters. Mathematically, we have $\rho, \rho(\alpha) \in \mathbb{R}^{p \times s}$ , where p is the number of measurements and s is the number of color channels. Also, we use bold font $\boldsymbol{\rho}$ to denote a BRDF with color (3 channels), and non-bold font $\rho$ to denote a single-channel BRDF. We use the PSNR values of rendered images of BRDFs under the environment map St. Peter's Basilica [Debevec 1998] before gamma correction to quantitatively compare different BRDFs. Since we don't have the groundtruth of diffuse and specular parts, we are only quantitatively comparing full BRDFs.

Step 1: analytic fitting. In the first step, we first approximate the achromatic reflectance $\overline{\rho}$ (average reflectance across color channels) of the target measured BRDF with a diffuse and a specular analytic BRDF:

$$\min_{\alpha_{\rm d}, \alpha_{\rm s}} d_1(\overline{\rho}, \rho_{\rm d}(\alpha_{\rm d}) + \rho_{\rm s}(\alpha_{\rm s})). \tag{3}$$

Here, $\alpha_{\rm d}$ is the parameter controlling the intensity of Lambertian BRDF $\rho_d(\alpha_d)$ , and $\alpha_s$ are the 3 GGX parameters of the specular analytic BRDF $\rho_s(\alpha_s)$ . We compared the results of the traditional non-convex optimizations using four types of metrics:

<span id="page-2-4"></span>cubic-root:
$$d_{1}(\rho_{1}, \rho_{2}) = \left\| ((\rho_{1} - \rho_{2}) \cdot \operatorname{cosMap})^{\frac{2}{3}} \right\|_{1}$$

$$\log 1: \qquad d_{1}(\rho_{1}, \rho_{2}) = \left\| \log \left( \frac{\rho_{1} \cdot \operatorname{cosMap} + \varepsilon}{\rho_{2} \cdot \operatorname{cosMap} + \varepsilon} \right) \right\|_{1}$$

$$\log 2: \qquad d_{1}(\rho_{1}, \rho_{2}) = \left\| \log \left( \frac{\rho_{1} \cdot \operatorname{cosMap} + \varepsilon}{\rho_{2} \cdot \operatorname{cosMap} + \varepsilon} \right) \right\|_{2}$$

$$\text{weighted-square: } d_{1}(\rho_{1}, \rho_{2}) = \left\| w \cdot ((\rho_{1} - \rho_{2}) \cdot \operatorname{cosMap})^{2} \right\|_{1}$$

$$(4)$$

<span id="page-2-2"></span>
$$\cos \operatorname{Map} = \max \{ \cos(\mathbf{n} \cdot \boldsymbol{\omega}_{i}) \cos(\mathbf{n} \cdot \boldsymbol{\omega}_{o}), \varepsilon \}, \tag{5}$$

where $\mathbf{n}$ , $\boldsymbol{\omega}_i$ and $\boldsymbol{\omega}_o$ are the normal, incoming light and outgoing light directions of each MERL measurement, and we use the product of their cosine terms to reduce the impact of extreme high values at grazing angles. To avoid a singularity at zero, we set $\varepsilon = 10^{-3}$ in log-based metrics. The weighted-square metric was first used by Ngan et al. [2005], where w is the solid angle for each MERL measurement. Fores et al. [2012] recently showed that cubic-root performs better, and reported that the log-based metric usually results in over-blurred highlights.

The results of the four different metrics are shown in Fig. 3, and there are two important observations: First, using the weighted-square metric usually cannot yield faithful results, mainly because it is over-emphasizing the highlights at the expense of ignoring the diffuse parts.

<span id="page-2-1"></span><sup>1</sup> Note that Ngan 2005 used equal-size binning, while the public dataset has non-uniform binning to better capture highlight shape. Thus, there are more large-value highlights in the public dataset, and weighted-square incorrectly gives more attention to these highlights, performing worse than expected.

<span id="page-3-0"></span>![](_page_3_Figure_1.jpeg)

Fig. 3. The results of the first two steps of our separation algorithm. In step 1, we found that the weighted-square metric can't produce faithful results, and none of the other three metrics (cubic-root, log1, log2) performs consistently well on all BRDFs. However, the fitting results of all these three metrics leads to good separations in step 2. We choose to use the log2 metric in the following since it produces shorter tails on the specular parts. Note that we are working only on achromatic reflectances in this step.

<span id="page-3-1"></span>![](_page_3_Figure_3.jpeg)

Fig. 4. The shape of our results in the first two steps. With the result of the first step as guidance, the result of the second step faithfully recovers the shape of the original BRDF.

The quantitative comparisons on all the test cases (Tab. 1) show that cubic-root, log1, and log2 metrics have better results than weighted-square. Second, the cubic-root, log1, and log2 metrics can only perform well on some materials: the log-based metrics faithfully recover the highlights in the second row of Fig. 3, and in the third row, the cubic-root metric better preserves the shape of the highlights. We continue the comparison on these three metrics in the second step.

Step 2: Diffuse-Specular separation. In this step, we seek exact solutions for the diffuse and specular parts of the measured BRDF, under the guidance of the analytic BRDF from the previous step. We

want the diffuse part $\rho_d$ and the specular part $\rho_s$ to sum up to the channel-average $\overline{\rho}$ of the original measured BRDF, while keeping each part close to the corresponding analytic approximation. In particular, we solve the following optimization problem:

$$\min_{\rho_{d},\rho_{s}} d_{2}(\overline{\rho}, \rho_{d} + \rho_{s}) + \eta^{d} \cdot d_{2}(\rho_{d}, \rho_{d}(\alpha_{d})) + \eta^{s} \cdot d_{2}(\rho_{s}, \rho_{s}(\alpha_{s})), \tag{6}$$

$$d_2(\rho_1, \rho_2) = \|(\rho_1 - \rho_2) \cdot \text{cosMap}\|_1. \tag{7}$$

The first term of the optimization supervises the difference between the sum of diffuse and specular parts and the original BRDF, and the last two terms add penalties to the differences between each part and its analytic approximation. This optimization problem involves solving millions of unknown variables; thus we use a linear BRDF metric in order to make the problem convex and easy to solve. We set the regularizer parameters to be $\eta^d=0.9, \eta^s=0.8$ , and we empirically found that this works for every BRDF in the MERL dataset. We will discuss the numerical details of the optimizations in Sec. 3.2.

We compare the results of the second step using three different analytic guidances (cubic-root, log1, and log2) from the first step, and the results are shown in Fig. 3. Although there are differences between these three analytic guidances, the final results of the separation look almost the same and all match the groundtruth very well (step 2 in Fig. 3). The extremely high PSNR values of the reconstructed BRDFs in Tab. 1 also show that using any one among these three as guidance could faithfully reconstruct the shape of the original BRDF. Notice that using the log2 metric tends to result in higher values in the diffuse term. This means the specular part of the measured BRDF will have a shorter tail, which is observed in analytic models [McAuley et al. 2012]. Thus, we use the results of the log2 metric in the following.

<span id="page-4-0"></span>Table 1. Quantitative results of our 3-step optimization compared with other single-step separation algorithms. We show the average PSNR values on all materials in the MERL dataset for each method. In the first step, cubic-root, log1, and log2 have better performances. In the second step, the PSNR values rise to an extremely high level for all three kinds of guidances, which means all of them yield almost exact reconstructions. The PSNR values drop in the third step since color is now considered. Compared to other single-step methods, our 3-step optimization can have much more accurate reconstructions. Notice that since we don't have the ground truth for the diffuse and specular parts, we are only computing the differences between the images of full BRDFs, in order to evaluate the PSNR numbers.

| category         | step                   | metric                 | PSNR  |
| ---------------- | ---------------------- | ---------------------- | ----- |
|                  |                        | cubic-root             | 41.34 |
| Ours             | step 1                 | log1                   | 40.97 |
|                  | (Achromatic)           | log2                   | 39.91 |
|                  |                        | weighted-square        | 28.84 |
|                  | step 2<br>(Achromatic) | cubic-root as guidance | 159.9 |
|                  |                        | log1 as guidance       | 162.2 |
|                  |                        | log2 as guidance       | 162.7 |
|                  | step 3                 | brdf-based             | 52.11 |
|                  | (Full BRDF)            | image-based 2-norm     | 55.34 |
| 1 step<br>method |                        | direct NMF             | 47.16 |
|                  |                        | Lawrence et al.        | 15.46 |
|                  |                        | Nielsen et al.         | 42.05 |

the log2 metric in the following. The shapes of the reconstructed BRDFs are shown in Fig. 4. Although we are using Lambertian and GGX models to guide the diffuse and specular parts, the results still keep many features in the measured models, rather than being restricted to the analytic forms.

Step 3: Color restoration. After we obtain the exact diffuse and specular parts of the measured BRDF, in the final step, we find the color for each part. Specifically, we determine the diffuse and specular colors $c_d$ , $c_s$ by solving the optimization problem with a properly chosen color metric $d_3(\rho_1, \rho_2)$ :

$$\min_{\mathbf{c}_{d}, \mathbf{c}_{s}} d_{3} \left( \boldsymbol{\rho}, \rho_{d} \cdot \mathbf{c}_{d} + \rho_{s} \cdot \mathbf{c}_{s} \right). \tag{8}$$

There are mainly two ways to compare the color of the BRDF: one is to compare the colors of raw BRDF values, and the other one is to do the comparison on the rendered images of BRDFs [Pereira and Rusinkiewicz 2012; Sun et al. 2017]. We compute the color differences in the HSI color space since its definition naturally extends to values larger than 1. Here, we compared the results of color restoration using two types of color metrics:

brdf-based:
$$d_3\left(\boldsymbol{\rho}_1,\boldsymbol{\rho}_2\right) = HSI(\boldsymbol{\rho}_1,\boldsymbol{\rho}_2),$$

image-based: $d_3\left(\boldsymbol{\rho}_1,\boldsymbol{\rho}_2\right) = HSI(\mathbf{R}\cdot\boldsymbol{\rho}_1,\mathbf{R}\cdot\boldsymbol{\rho}_2),$ (9)

where R is the light transport matrix transferring a BRDF into an image, and $HSI(\mathbf{x}_1, \mathbf{x}_2)$ is the metric of the HSI color space defined as:

$$HSI(\mathbf{x}_{1}, \mathbf{x}_{2}) = \|\mathbf{s}_{1} \cos \mathbf{h}_{1} - \mathbf{s}_{2} \cos \mathbf{h}_{2}\|_{2} + \|\mathbf{s}_{1} \sin \mathbf{h}_{1} - \mathbf{s}_{2} \sin \mathbf{h}_{2}\|_{2}.$$
(10)

Here, $\mathbf{s}$ and $\mathbf{h}$ are the saturation and hue value of $\mathbf{x}$ . Since we have ensured that $\overline{\rho} = \rho_d + \rho_s$ in the second step, we are not considering the intensity i here. We use the environment lighting St. Peter's

<span id="page-4-2"></span>![](_page_4_Figure_12.jpeg)

Fig. 5. The results of the color restoration step using different color metrics. We observe that the image-based metric is slightly better than the brdf-based metric.

Basilica [Debevec 1998] in the image rendering. For the fitting, we only use one scan line in the middle of the image, but the resulting PSNR in Tab. 1 is computed on the whole image.

The color restoration results for the two different metrics are shown in Fig. 5. We found that the image-based metric performs better than the brdf-based metric (see the error map in Fig. 5), since the image-based metric weights each BRDF entry by its contribution to the final image while the brdf-based metric weights each measurement equally. The quantitative comparison results in Tab. 1 also show that the image-based metric has better performance on color restoration. Due to these observations, we use the result of the image-based metric in our results. Note that we only use the image-based metric in this step. For the first two steps, we use BRDF-based metrics. Please refer to the supplementary material for more validations under different lighting environments.

#### <span id="page-4-1"></span>3.2 Results

Setup. We run our 3-step optimization on all of the materials in the MERL dataset. We use the MATLAB function fmincon to optimize the first and third step, and use the CVXOPT package to handle the second step. Each BRDF needs around 5 minutes to do the separation, and about 90% of the time is used in the second step.

Comparison. We compared our diffuse-specular separation algorithm with other separation algorithms. The separation results are shown in Fig. 6, and the quantitative results are listed in Tab. 1. One simple approach for separation is to directly apply non-negative matrix factorization (NMF) on the BRDF. Although the reconstructed results look similar to the original BRDF, this method doesn't have the concept of diffuse and specular, and therefore doesn't have a clean and meaningful separation. The algorithm proposed by Lawrence et al. [2006] used statistical priors to constrain the shape of diffuse and specular parts, and mixed the color together with the reflectances. As a result, their method can't preserve the colors very well. The method from Nielsen et al. [2015] decomposes the BRDF into 5 principal components in log space. We take the second component as the diffuse part (as stated in their paper) and the rest as the specular part. Since it mixed the diffuse and specular part

<span id="page-5-1"></span>![](_page_5_Figure_1.jpeg)

Fig. 6. Compared to other diffuse-specular separation approaches, our algorithm produces a more reasonable separation and better keeps the color.

<span id="page-5-2"></span>![](_page_5_Figure_3.jpeg)

Fig. 7. Plot and images of nickel, its specular component, and its specular analytic fitting along the mirroring directions. The BRDF value is the average value across all color channels. Our optimization is guided by the analytic specular BRDF, but we avoid its high values at the grazing angles in the final result. The separated specular part faithfully models the original BRDF.

together when doing the principal component analysis, it doesn't yield a meaningful separation. We also compared with an image-based separation algorithm [\[Shi et al.](#page-14-34) [2017\]](#page-14-34), where the input is the image of the BRDF rather than the raw BRDF values. Due to the ambiguity between shape and BRDF, their separation results fail to recover the color and the appearance. In comparison, starting with an analytic fitting, our method could generalize the concept of diffuse and specular to the space of measured BRDFs. Thus, compared to other single-step algorithms, our 3-step algorithm could faithfully reproduce the appearances and colors for both diffuse and specular parts in all kinds of materials.

Grazing angles. The specular component from our separation largely follows the shape of the original measured BRDF at grazing angles. To test this, Fig. [7](#page-5-2) plots the average BRDF values across the color channels of nickel along the mirroring directions (i.e., plots of different $\theta_d$ values for $\theta_h = 0$). Since nickel is a metal, the diffuse component is very small and the BRDF can essentially be

<span id="page-5-3"></span>![](_page_5_Picture_7.jpeg)

Fig. 8. Limitation of our diffuse-specular separation. We can't reproduce the color of a material with multiple colors in its specular part.

represented by only the specular component. Although the analytic specular BRDF has very high values at the grazing angles because of Fresnel effects, the specular component from the diffuse-specular separation by our method is very accurate, largely following the curve of the original BRDF. Since the MERL dataset was captured using spheres [\[Matusik et al.](#page-14-3) [2003a\]](#page-14-3), the pixel footprints cover a large region at the grazing angle. As a result, the BRDF values are much lower at grazing angles than predicted by analytic models [\[Holzschuch and Pacanowski 2017\]](#page-14-19).

Limitation. Figure [8](#page-5-3) shows a failure case of our separation, where the color on the material is changing due to diffraction. As a result, the color restoration algorithm can only yield an average color for its specular part.

# <span id="page-5-0"></span>4 MEASURED BRDF EDITING

A measured BRDF can be used in a much more flexible way after diffuse-specular separation in the form of Equ. [1.](#page-1-1) In this section, we show new types of simple editing operations, which have been straightforward for analytic BRDFs but have not so far been easy to do for measured BRDFs [\[Matusik et al.](#page-14-35) [2003b;](#page-14-35) [Tsirikoglou et al.](#page-14-36) [2016;](#page-14-36) [Serrano et al.](#page-14-37) [2016;](#page-14-37) [Sun et al.](#page-14-33) [2017\]](#page-14-33). In Sec. [5,](#page-6-1) we develop a compact representation of measured BRDFs after principal component analysis on the separated diffuse and specular parts, while Sec. [6](#page-9-0) relates measured and analytic BRDFs and demonstrates robust and efficient analytic fitting.

Editing Colors. The key point of the separation is to decouple the diffuse and specular parts, and then decouple the color from each reflectance. One can then apply traditional color theory to change the color for each part independently. We express the color in the HSI space, which allows us to tune the hue and the saturation easily. Editing the diffuse color is shown in Fig. [9a](#page-6-0). Notice that the color and the shape of the highlights do not change when we alter the diffuse color. We are also allowed to change the specular hue of a measured BRDF (Fig. [9b](#page-6-0)).

Color editing is straightforward in analytic BRDFs, since it's defined as the sum of the diffuse and specular parts, each with a single color. Some previous work has tried to edit measured BRDF colors, but this has always been difficult, since each BRDF sample is a mixture of diffuse and specular parts, each with its own color. Matusik et al. [\[2003a\]](#page-14-3) labelled the BRDF with the color, while Serrano et al. [\[2016\]](#page-14-37) embed the color information into the representation of achromatic reflectances. However, the colors are still not intuitive or

<span id="page-6-0"></span>![](_page_6_Figure_2.jpeg)

Fig. 9. Our diffuse-specular separation gives measured BRDFs a lot more flexibility. We can change (a) the diffuse color and (b) the specular color of the measured BRDF, without affecting the other part. We can also (c) do a highlight removal on the BRDF space. In addition, we can (d) create new measured BRDFs by taking the diffuse and specular parts from two different measured BRDFs and mixing them together.

well-defined. One can also imagine changing the color using image-enhancing software such as Photoshop. However, since it doesn't have the concept of diffuse and specular, changing the diffuse color might also affect the color of specular highlights. With our method, we can treat the color of the diffuse and specular part separately, and perform intuitive editing in the HSI color space.

Highlight Removal. Our separation algorithm enables us to remove the highlights on measured BRDFs by simply controlling the ratio of the specular to the diffuse component. As shown in Fig. 9c, the leftmost bunny with a very glossy surface gradually becomes a bunny with no highlights. Previous highlight removal algorithms usually focus on removing highlights in images, which contain information on both the material and the lighting. For our method, we are doing the highlight removal only on the BRDF space.

Mixing Reflectances. Separating the diffuse and specular parts also allows us to recombine them from different materials. Figure 9d shows an example of mixing the diffuse and specular parts from different measured BRDFs. Although we are still not capable of editing the roughness or the index of refraction of the reflectances as in analytic models, we can generate novel BRDFs by choosing the desired diffuse and specular parts from the dataset and then mixing them together. Since the measured BRDFs are essentially lookup tables, this kind of edit was previously not possible on measured BRDFs.

#### <span id="page-6-1"></span>5 COMPACT MEASURED BRDF MODEL

We now investigate a compact measured BRDF model enabled by the diffuse-specular separation. We conduct principal component analysis (PCA) on both the diffuse and specular components. Previously, Nielsen _et al._ [2015] used PCA on the MERL dataset and found that measured BRDFs lie in a low-dimensional space. However, they treated each color channel independently and the contributions of diffuse and specular parts were mixed together. By doing PCA on the diffuse and specular parts separately, we can yield a more intuitive and more compressed result.

#### 5.1 Methods

Diffuse. The separation results in Sec. 3 show that the structure of diffuse BRDFs is relatively simple. Thus, we directly do the principal component analysis on the diffuse parts of all measured BRDFs from the MERL dataset. We didn't subtract the mean when doing PCA, since we want our model to be similar to the Lambertian model, which can be scaled by a single intensity parameter $\alpha_d$ . The result of PCA shows the high redundancy of information in the diffuse part: around 99% of the energy is concentrated in the first principal component. The images of a diffuse BRDF reconstructed using 1 and 2 principal components (Fig. 10) further shows that the diffuse part lies in a very low dimensional space. Thus, we choose to represent the diffuse BRDF of measured materials using only 1 principal component:

$$\rho_{\rm d} = Q_{\rm d} \cdot x_{\rm d},\tag{11}$$

where $Q_d \in \mathbb{R}^{p \times 1}$ is the first principal component learned by PCA, and $x_d$ is the coefficient that corresponds to the first principal component.

We also present a comparison between the Lambertian model and the shape of the first principal component in Fig. 10. The principal component largely models the Lambertian model, and has some fall off at the grazing angles. The diffuse falloff at grazing angles comes from numerical issues, and has little effect on the final images, as shown in the sphere images of Fig. 10. Specifically, the weighting term cosMap (Equ. 5) becomes very small at grazing angles. If the values of the diffuse BRDF are also small (around $10^{-3}$ or smaller, which is the case for about 30% of the MERL dataset, mostly metals), then the multiplied values will be too small to robustly optimize for.

The relatively simple structure of the diffuse parts allows us to draw a direct mapping from the diffuse part of measured BRDF to the Lambertian model. Given the diffuse part of a measured BRDF $\rho_{\rm d}=Q_{\rm d}\cdot x_{\rm d}$ , we can get the exact form of the corresponding Lambertian BRDF $\rho_{\rm d}(\alpha_{\rm d})=\frac{\alpha_{\rm d}}{\pi}$ :

<span id="page-6-2"></span>
$$\alpha_{d} = \underset{\alpha}{\operatorname{argmin}} \|Q_{d} \cdot x_{d} - \rho_{d}(\alpha)\|_{2}^{2}$$

$$\alpha_{d} = \frac{\pi \cdot \|Q_{d}\|_{2}^{2}}{\|Q_{d}\|_{1}} \cdot x_{d}.$$
(12)

<span id="page-7-0"></span>![](_page_7_Figure_1.jpeg)

Fig. 10. Reconstruction results of the diffuse part of a measured BRDF using principal component analysis. Using 1 principal component (PC) is sufficient to recover the appearance of the diffuse part.

This equation shows the linear relation between the analytic parameter $\alpha_{\rm d}$ and measured PC coefficient $x_{\rm d}$ , which enables simple conversion between the Lambertian model and our model of diffuse BRDFs.

_Specular._ The specular parts show much more complicated behaviors. We use the log-relative mapping [Nielsen et al. 2015] before doing PCA:

<span id="page-7-3"></span>
$$g(\rho_{\rm s}) = \log \left( \rho_{\rm s} \cos \text{Map} + \varepsilon \right),$$
(13)

where the weight cosMap is used to avoid the high values in grazing angles, and $\varepsilon$ is still $10^{-3}$ to avoid a singularity at zero. After doing the mapping, the values of the measured BRDFs are projected into a log space, where highlights and off-peak parts are comparable. Compared to the mapping from Nielsen _et al._ [2015], we omitted the denominator in the log function, since it will only result in a mean shift in PCA. We then do the principal component analysis on the mapped values, so that the specular part can be expressed as:

$$\rho_{\rm s} = g^{-1} \left( \mathbf{Q}_{\rm s} \cdot \mathbf{x}_{\rm s} + \mu_{\rm s} \right), \tag{14}$$

where $Q_s$ are the learned principal components, $\mathbf{x}_s$ are the corresponding coefficients, and $\mu_s$ is the shifted average for the mapped values. $g^{-1}(\cdot)$ is the inverse function of the log mapping $g(\cdot)$ . In Fig. 11, we show that using 3 principal components is sufficient to reconstruct almost all kinds of specular parts in the MERL dataset. We can recover the overall intensity (chrome) as well as the highlight shape (yellow-matte-plastic), compared with using only 2 principal components. The reconstructed BRDF at each channel also matches the specular part very well (blue-metallic-paint2).

Figure 12 shows the principal components visualized as BRDF slices [McAuley et al. 2012], compared with the principal components from Nielsen _et al._ Since we have separated the diffuse and specular term, we don't observe diffuse terms in the principal components: the sharp highlights usually observed in metals and plastics are mostly contained in the first principal component; the second principal component models the width of the highlights which comes from the roughness of the surface; the third principal component controls the Fresnel effect of the material; the shapes of specular highlights and Fresnel terms are further refined by the last two principal components. On the other hand, the second principal component from Nielsen _et al._ mixed the diffuse and the scattered highlights together. Thus, their method requires more principal components to model the appearance.

<span id="page-7-1"></span>![](_page_7_Picture_10.jpeg)

Fig. 11. Reconstructed specular parts of the measured BRDFs using different numbers of principal components (PCs). The first row shows the specular shapes of blue-metallic-paint2 under different reconstructions. These are value vs angle plots in a polar coordinate system for in-plane measurements; the different colors denote the RGB components. We found that using 3 principal components can faithfully reproduce a wide range of specular appearances (chrome and yellow-matte-plastic) in the MERL dataset. Please zoom in to see the small differences between rendered materials.

<span id="page-7-2"></span>![](_page_7_Figure_12.jpeg)

Fig. 12. Comparison of the BRDF slices of the specular principal components using our method and Nielsen _et al._ 's. We don't need a principal component to model the diffuse part like the second component of Nielsen _et al._ 's, thus our method yields more compact results.

#### 5.2 Results

We compare our results to the method from Nielsen _et al._ [2015] in Fig. 13. Our method differs with the previous method in two ways. First, we do the analysis on the diffuse and specular parts of the measured BRDFs separately, whereas the previous method directly applied on the whole BRDFs. As a result, the materials reconstructed by our method have less ringing artifacts compared to the previous method (third row of Fig. 13). Second, we have extracted the colors from the BRDF and do the analysis only on the achromatic reflectances, while the training data from the previous method still contains color dependencies. Due to these two key changes, our

<span id="page-8-0"></span>![](_page_8_Figure_2.jpeg)

Fig. 13. Full BRDFs reconstructed using our method, compared with the method from Nielsen et al.

method can express a measured BRDF in a more compact and efficient way. Please refer to the supplementary material for more

Figure 14 shows the average reconstruction errors of all MERL BRDFs with our method, compared with those with Nielsen et al. Here, we use 2 parameters for each color (we model the RGB color to have average value 1), 1 principal component for the diffuse part, and vary the number of principal components for specular. Since we have separated the color from reflectance, our method yields small errors with fewer parameters compared with Nielsen et al., where they ignore the color coherence and use the same number of coefficients to reconstruct each color channel.

Our full measured model is expressed as:

<span id="page-8-4"></span>
$$\boldsymbol{\rho} = \mathbf{c}_{\mathrm{d}} \cdot Q_{\mathrm{d}} \mathbf{x}_{\mathrm{d}} + \mathbf{c}_{\mathrm{s}} \cdot g^{-1} \left( Q_{\mathrm{s}} \mathbf{x}_{\mathrm{s}} + \mu_{\mathrm{s}} \right). \tag{15}$$

For our method, only 8 coefficients (parameters) are needed to specify a full measured BRDF (1 for diffuse PC coefficient $x_d$ , 3 for specular PC coefficients $\mathbf{x}_s$ , and 2 for each normalized color $\mathbf{c}_d$ , $\mathbf{c}_s$ ), whereas previously 15 coefficients (5 coefficients for each color channel) were needed. Note that even for the analytic GGX or similar model, we also need 8 parameters<sup>2</sup> to specify a full BRDF. Note that our measured BRDF model is aimed at representing a material with one diffuse lobe and one specular lobe, which is the same as traditional analytic models. Thus, our method allows users to store measured BRDFs using the same amount of storage as analytic BRDFs, while faithfully keeping the accuracy of measured BRDFs.

### 5.3 Limitations

Figure 15 shows two failure cases of our approach. In the first row, using 3 specular coefficients is not sufficient to reproduce the complicated appearance of two-layer-gold, since the specular part of this material has two layers; however, we can accurately reproduce the reflectance by using 5 specular coefficients. The method from

Table 2. Quantitative results of our method using different numbers of parameters, compared with the method from Nielsen et al.

| Parameter Number    | 1   | 2     | 3             | 4     | 5        | 6             | 7        | 8        | 9             | 10       | 11       | 12            | 13       | 14        | 15            |
| ------------------- | --- | ----- | ------------- | ----- | -------- | ------------- | -------- | -------- | ------------- | -------- | -------- | ------------- | -------- | --------- | ------------- |
| Parameter (Nielsen) |     |       | $x^{RGB}_{1}$ |       |          | $x^{RGB}_{2}$ |          |          | $x^{RGB}_{3}$ |          |          | $x^{RGB}_{4}$ |          |           | $x^{RGB}_{5}$ |
| PSNR                |     |       | 23.3          |       |          | 34.0          |          |          | 40.2          |          |          | 41.7          |          |           | 44.0          |
| Parameter (Ours)    |     | $c_d$ | $x_d$         | $c_s$ | $x_{s1}$ | $x_{s2}$      | $x_{s3}$ | $x_{s4}$ | $x_{s5}$      | $x_{s6}$ | $x_{s7}$ | $x_{s8}$      | $x_{s9}$ | $x_{s10}$ |               |
| PSNR                |     | 28.8  | 34.7          |       | 40.2     | **42.0**      | 42.4     | 43.5     | 44.5          | 45.1     | 45.3     | 45.5          | 46.0     |           |               |

<span id="page-8-1"></span>![](_page_8_Figure_14.jpeg)

Fig. 14. Quantitative results of our method using different numbers of parameters, compared with the method from Nielsen et al. By doing the analysis on diffuse and specular parts separately, we can represent the BRDFs with fewer coefficients.

<span id="page-8-3"></span>![](_page_8_Figure_16.jpeg)

Fig. 15. Limitations of our measured BRDF model. Our model can't match the exact highlight shape of two-layer materials using 3 specular principal components (first row). Also, we can't recover the large Fresnel effect of some materials, which is possibly introduced by subsurface scattering.

Nielsen et al. gives a good reconstruction of this material, with the expense of using 15 coefficients in total. In the second row, the high values at grazing angles are not captured in our reconstruction results nor in the result from Nielsen et al. We believe this is because the high values come from the subsurface scattering of the material during measurement, rather than from the BRDF. Another limitation of our method is that we also need to store the precomputed principal components, rather than just the 8 coefficients. However, these principal components are the same for all measured BRDFs and need only be computed and stored once; we will make them available online upon publication.

<span id="page-8-2"></span><sup>2</sup> For GGX, each color needs 2 parameters. Diffuse part needs 1 to control the intensity, and specular part needs 3 to vary the intensity, roughness, and index of reflection (IOR).

#### <span id="page-9-0"></span>6 RELATING AND FITTING TO ANALYTIC BRDFS

The measured BRDF model introduced in Sec. 5 and Equ. 15 can compress a measured BRDF to the same size as an analytic BRDF. This compact expression enables a direct mapping between the diffuse part of the measured and analytic models (Equ. 12), and embeds the specular part of the measured BRDF in a low-dimensional principal component (PC) space. In this section, we study the relation between the _specular_ parts of the measured and analytic BRDFs in the PC space, and show their similarities and differences. Based on the analysis, we further introduce a robust, efficient, and simple fitting algorithm for complex materials with two-lobe specular parts.

### 6.1 Joint Training

In order to compare and analyze two different BRDF models, we project the analytic BRDFs onto the space spanned by the principal components. However, since the measured principal components are trained only on measured data, they only encode the structure of measured BRDFs. As a result, directly projecting analytic BRDFs leads to artifacts, as shown in the second row of Fig. 16. In order to resolve this problem, we include 128 specular BRDFs from the GGX model, and redo a joint principal component analysis together with the original measured specular BRDFs. $^3$ In this way, we can slightly modify the principal components to also model the structure of the analytic BRDFs. We call the new principal components the joint principal components $Q_{s,joint}$ , and the spanned space as joint-PC space.

Figure 16 illustrates the joint principal components and the original measured principal components. Previously, the first measured principal component has some fall-off at the grazing angle, since the original measurements are unreliable in this region. By including analytic BRDFs, the first principal component includes a more obvious Fresnel effect (see the upper-right corner of PC 1). Also, the scattered highlight part in the second joint principal component extends more to the grazing angle. We also included the principal components trained with solely analytic BRDFs, and we can observe how the joint principal components contain features from both the analytic and measured BRDFs. The last two columns of Fig. 16 show an analytic BRDF and a separate measured BRDF projected to different PC spaces. Compared to the original PC space which is trained only on measured data, the joint-PC space can better preserve the appearances of analytic BRDFs (the analytic BRDFs shown here are not presented in the training data). In the last column, we demonstrate that including analytic data into training does not introduce visible artifacts to the reconstructed measured BRDFs, while training only analytic BRDFs may lead to some intensity mismatch (please zoom in to see the difference in the last column). In other words, the joint principal components can represent both analytic and measured BRDFs.

<span id="page-9-1"></span>![](_page_9_Figure_7.jpeg)

Fig. 16. The first three principal components trained from solely measured BRDFs in MERL dataset (second row), from analytic and measured BRDFs together (third row), and from solely analytic BRDFs (last row). We also compare the reconstruction results under these three spaces. By including analytic BRDFs into training, we can better recover the appearances of analytic BRDFs (fourth column), while still keeping the fidelity of measured BRDFs (last column).

### 6.2 Analytic Gamut in Joint-PC Space

We now densely sample 16,000 analytic parameters from the GGX model<sup>4</sup>, and project each analytic BRDF to the joint-PC space after the log-relative mapping g (Equ. 13), according to the equation:

<span id="page-9-4"></span>
$$\begin{aligned} \mathbf{x}_{s} &= \underset{\mathbf{x}}{\operatorname{argmin}} \ \left\| \left( \mathbf{Q}_{s,joint} \cdot \mathbf{x} + \mu_{s,joint} \right) - g(\rho_{s}) \right\|_{2} \\ &= \left( \mathbf{Q}_{s,joint}^{T} \cdot \mathbf{Q}_{s,joint} \right)^{-1} \cdot \mathbf{Q}_{s,joint}^{T} \left( g(\rho_{s}) - \mu_{s,joint} \right), \end{aligned} \tag{16}$$

where $Q_{s,joint}$ and $\mu_{s,joint}$ are the principal components and the mean from _joint training_. $\rho_s$ can be any specular BRDF to be projected; besides the densely-sampled analytic BRDFs, we also project the specular parts of all the measured BRDFs from the MERL dataset (specular MERL BRDFs) to the joint-PC space. After the projection, we can represent both analytic and measured BRDFs with a point in the joint-PC space. In Fig. 17, we visualize the projected analytic gamut and the measured BRDFs in the joint-PC space, which has three dimensions. We color-code the analytic points according to their intensity parameter $\rho_0$ (see Equ. 2), and mark all the specular MERL BRDFs as red. Notice that the analytic BRDFs here are all simple BRDFs with only one lobe.

As shown in the front view of Fig. 17, the analytic gamut lies in a thin manifold in the joint-PC space. It has a highly non-convex shape, which looks like a "baseball glove." Also, the intensity $\rho_0$ and the index of refraction n of the GGX model are correlated in the

<span id="page-9-2"></span><sup>3</sup> We take 4 intensity ($\rho_0$) samples from the range [0.01, 0.6], 8 roughness ($m$) samples from [0.005, 0.8], and 4 IOR ($n$) samples from [1.3, 3.0]. We sample all three parameters in log space in order to have a uniform distribution in the PC space. This gives us $4 \times 8 \times 4 = 128$ analytic BRDFs. We pick the number 128 to roughly match the number of analytic BRDFs.

<span id="page-9-3"></span><sup>4</sup> We take 20 intensity ($\rho_0$) samples from [0.01, 0.6], 40 roughness ($m$) samples from [0.005, 0.8], and 20 IOR ($n$) samples from [1.3, 3.0], all in log space. This gives us $20 \times 40 \times 20 = 16{,}000$ analytic BRDFs.

<span id="page-10-0"></span>![](_page_10_Figure_2.jpeg)

Fig. 17. Analytic and measured BRDFs plotted in the joint-PC space. The red points are the specular parts of MERL BRDFs mapped to joint-PC space, and the blue-to-yellow points are projected analytic BRDFs color-coded with their intensity $\rho_0$ . Orange points (insets 1a - 5a) are some representative measured BRDFs, and light blue points (insets 1b - 5b) are their nearest analytic BRDFs in the analytic gamut. Measured BRDFs 1a and 2a lie inside the analytic gamut, and closely match their analytic counterparts 1b and 2b. Measured BRDFs 3a and 4a are far away from the analytic gamut and cannot be fit well by single-lobe analytic BRDFs. Measured BRDF 5a has sharp highlight, so its nearest analytic 5b matches its intensity but has blurry highlights. Analytic BRDF 5c is manually selected to match the highlight of (5a), but it fails to reproduce the overall intensity of 5a.

space. The roughness m is largely perpendicular to the other two parameters, and has a high impact on the appearance since its span is wider. This is to be expected, since increasing the intensity $\rho_0$ and IOR _n_ will both yield a BRDF with brighter highlights, while the roughness m mainly controls the width and the shape of the highlights.

The relative positions of the specular parts of MERL BRDFs (red points in Fig. 17) in the joint-PC space are also worth noting. In the back view of Fig. 17, we can see that not all the MERL BRDFs lie inside the analytic gamut. The measured materials on the right side of the back view, which have larger roughness values and smoother highlights, tend to coincide more with the analytic gamut. For instance, for the materials shown in insets 1a and 2a of Fig. 17, we can easily find corresponding analytic BRDFs in the analytic gamut, which are shown in insets 1b and 2b. We can also observe some measured materials that reside in the hollow part of the "baseball glove" outside the analytic gamut, such as insets 3a (violet-acrylic) and 4a (two-layer-gold) in Fig. 17. Often, the specular parts of these materials consist of more than one lobe.

The measured BRDFs on the left side of the back view sometimes lie above the analytic gamut. As a result, for the specular part shown in inset 5a, we cannot easily find an analytic BRDF with a similar appearance. The material shown in inset 5b has mismatches on the highlights but keeps the overall intensity. Another analytic BRDF in inset 5c has a more similar highlight shape, but the intensity becomes lower. There are mainly two reasons that contribute to this mismatch. First, since the analytic BRDF is only an approximation, the model is not accurate enough to capture the measured data. Second, the measured BRDF might be the sum of the BRDFs from multiple lobes, which can't be represented by a one-lobe analytic BRDF. As we will show in Sec. 6.3, our framework can resolve the multi-lobe problem in a robust and efficient way.

### <span id="page-10-1"></span>6.3 Robust and Efficient BRDF Fitting

With the analytic and measured BRDFs projected to the same space, we further investigate the problem of finding an analytic BRDF with the closest appearance to a measured BRDF. The analytic formula for fitting the diffuse part is given in Equ. 12. Here, we focus on fitting only the specular parts of BRDFs.

<span id="page-11-2"></span>![](_page_11_Figure_1.jpeg)

Fig. 18. The one-lobe fitting result of our nearest neighbor fitting algorithm compared with the traditional log2 fitting. The two results are very similar to each other since our nearest neighbor search is essentially finding the $L_2$ optimum in a log space. Nevertheless, our fitting is more efficient and can find the global optimum.

6.3.1 BRDF Metric. Following the metric used in Equ. 16, we define the BRDF metric on the joint-PC space as the squared $L_2$ norm of the BRDF after the log-relative mapping (Equ. 13). For each data point in the joint-PC space, this metric can be computed as

$$d(\mathbf{x}_{s1}, \mathbf{x}_{s2}) = \| (\mathbf{Q}_{s,joint} \cdot \mathbf{x}_{s1} + \mu_{s,joint}) - (\mathbf{Q}_{s,joint} \cdot \mathbf{x}_{s2} + \mu_{s,joint}) \|_{2}^{2}$$

$$= \| \mathbf{Q}_{s,joint} \cdot (\mathbf{x}_{s1} - \mathbf{x}_{s2}) \|_{2}^{2},$$

$$= (\mathbf{x}_{s1} - \mathbf{x}_{s2})^{T} \cdot \mathbf{Q}_{s,joint}^{T} \mathbf{Q}_{s,joint} \cdot (\mathbf{x}_{s1} - \mathbf{x}_{s2}).$$
(17)

Notice that the joint principal components are orthogonal to each other by definition, thus the matrix $\mathbf{Q}_{s,joint}^T \mathbf{Q}_{s,joint}$ is a diagonal matrix. If we further normalize each principal component to have $L_2$ norm 1, then the distance metric becomes simply:

<span id="page-11-0"></span>
$$d(\mathbf{x}_{s1}, \mathbf{x}_{s2}) = \|\mathbf{x}_{s1} - \mathbf{x}_{s2}\|_{2}^{2}. \tag{18}$$

This equation means that the BRDF metric on the joint-PC space can be easily computed by the $L_2$ distance of the joint-PC coefficients.

6.3.2 One-lobe Fitting. The BRDF metric defined in Equ. 18 leads to a simple and efficient one-lobe fitting algorithm: we can project the specular part of the target measured BRDF onto the joint-PC space, and then find the nearest neighbor from the analytic gamut. <sup>5</sup> The insets in Fig. 17 show some results of the nearest neighbor fitting: As discussed before, the smooth measured BRDFs (1a, 2a) can easily find very similar corresponding materials (1b, 2b) in the analytic gamut. For materials with multiple lobes in their specular parts (3a, 4a), it's almost impossible to find one-lobe analytic BRDFs in the gamut that have similar appearances (see the one-lobe fitting results in 3b and 4b). The materials in the right side of the back view (5a) contain sharp highlights, and their nearest analytic BRDFs (5b) usually have blurry highlights. There also exist materials in the gamut that better match their highlights (5c), but the accuracy in the low-intensity parts is sacrificed.

Figure 18 shows that our results have similar highlights as $\log 2$ fitting. Note that we are essentially doing the same optimization as the $\log 2$ fitting (see Equ. 4 for the exact metric), since we are finding the $L_2$ -minimum after a $\log$ mapping. Since the $\log$ minimum function places more penalty on the $\log$ -value mismatch, we yield blurry highlights for the material shown in Fig. 18. However, we perform

<span id="page-11-3"></span>![](_page_11_Picture_11.jpeg)

Fig. 19. An overview of the direct projection and iterative projection. For direct projection, we only process till (2b), and our final result is (1b) + (2b). For iterative projection, we iteratively calculate the residual and project it onto the analytic gamut using nearest neighbor search until convergence.

<span id="page-11-4"></span>![](_page_11_Figure_13.jpeg)

Fig. 20. We present a 2D view of the 3D analytic gamut. In our stratified search algorithm, we present the gamut represented using a hierarchy of strata. At each level, we divide the current stratum into several small strata with k-means clustering. During searching, we only evaluate the center point of each stratum, and then proceed to the next level by restricting our searching area to the stratum with the lowest fitting errors on its center.

the optimization in an efficient and globally optimal way, which will benefit the two-lobe fitting algorithms we will introduce next.

6.3.3 Two-lobe Fitting. Since one lobe is not sufficient to accurately model the specular parts of some measured BRDFs, we develop a two-lobe fitting algorithm. Our goal is to find two analytic BRDFs whose sum most closely matches the target specular part. Notice that although we can represent analytic BRDFs as the joint-PC coefficients in the joint-PC space, we can't directly add the coefficients together since the joint-PC space is constructed with logarithm mapping. Thus, we have to consider the residual in the BRDF space:

$$\operatorname{Residual}_{\rho_{s}}(\alpha_{s}^{(1)}) = \rho_{s} - \rho_{s}(\alpha_{s}^{(1)}), \tag{19}$$

where $\rho_s$ is the specular part of the target measured BRDF, and $\rho_s(\alpha_s^{(1)})$ is the analytic BRDF of the first lobe.

One straightforward algorithm is to first do a nearest neighbor fitting for the target measured BRDF, then do another nearest neighbor fitting on the residual. We call this algorithm _direct projection_. However, this greedy method cannot yield an optimum. An improved version of this algorithm is to do an _iterative projection_: at each step, we fix the BRDF of one lobe, and do the nearest neighbor

<span id="page-11-1"></span><sup>5</sup> We use the nearest neighbor library from the Python package _sklearn_, which uses a KD-tree to do the nearest neighbor search.

<span id="page-12-0"></span>![](_page_12_Figure_2.jpeg)

Fig. 21. Analytic fitting results using different algorithms. Compared to the traditional non-convex optimization using different metrics, the stratified search algorithm can reproduce the full measured BRDF in a more robust and efficient way. The leftmost column shows one-lobe nearest neighbor fitting as a baseline.

fitting for its residual; we alternate between lobes until it converges. Figure [19](#page-11-3) illustrates the basic idea of these two algorithms. Although the iterative projection algorithm is efficient and is able to find an optimal solution, we can only guarantee a local optimum.

We can also solve this problem in a brute-force way. Notice that once we determine the analytic BRDF of the first lobe, we can immediately find the second-lobe BRDF by doing a nearest neighbor fitting on the residual. By enumerating all possible first-lobe BRDFs in the analytic gamut, we can just pick the one which yields the lowest reconstruction error. Clearly, this exhaustive search is robust and can guarantee a globally optimal solution, but the enumeration is time-consuming.

In order to improve the time efficiency, we exploit the smoothness and locality of the gamut. An overview of our stratified search algorithm is shown in Fig. [20.](#page-11-4) We first construct a hierarchy of strata on the analytic gamut by dividing the gamut into several small strata using k-means clustering, and recursively dividing each small stratum until each stratum is left with sufficiently few analytic points. In practice, we divide each stratum into 12 small strata, and allow them to have some overlap. In this way, the hierarchy has 4 levels, where the strata in the lowest level have no more than 80 analytic points. This kind of hierarchical structure enables us to search for the optimum efficiently. When we are given the specular part of a measured BRDF, we first enumerate the first-lobe analytic BRDF from only the centers of the strata in the first level, which is simply the full analytic gamut. We then directly obtain the second-lobe BRDF by finding the closest analytic point of the residual in the full gamut using nearest neighbor fitting as usual. After that, we pick the center which produced the lowest fitting error, and continue to search in its stratum in the next level of the hierarchy. Algorithm [1](#page-13-0) details the construction and searching algorithm.

We build the stratified search algorithm under the assumption that the adjacent points in the analytic gamut have similar appearances. In this way, we can avoid searching for all possibilities. However, we cannot strictly guarantee a global optimum, since the discretization of the strata may slightly miss the optimum near the boundary. We call our result stratified global optimum, since it is the global optimum under this stratification. Table [3](#page-13-1) shows that in practice the results are very close to the global optimum from exhaustive search.

6.3.4 Results. We fit all the full measured BRDFs in the MERL dataset with one Lambertian for diffuse and two GGX BRDFs for specular. We use Equ. [12](#page-6-2) to map measured diffuse parts to Lambertian, and we use the colors from the diffuse-specular separation. The summary for different fitting algorithms is shown in Tab. [3.](#page-13-1) Since we assume we already have the result of diffuse-specular separation, we only count the runtime for fitting. We compare our algorithms with traditional non-convex optimization, where all the parameters and colors are solved in one optimization (using a standard interior-point method).

One interesting finding in Tab. [3](#page-13-1) is that the direct projection produces worse results than one-lobe fitting. This is mainly because the residual of the one-lobe fitting result might not be a valid BRDF, so a direct projection of the residual will add artifacts to the final result. The performance increases a little when we do the iterative projection. As we can see, the stratified search algorithm has the best balance between the robustness and efficiency. Compared to the traditional non-convex optimizations, our algorithm can yield better results with less time. We also examine the robustness of the stratified search algorithm by comparing it with the exhaustive search. We test both algorithms on 10 materials which clearly need two lobes to model their specular parts. The results indicate that the stratified search algorithm can yield a result which is very close to the global optimum in practice with much less time than exhaustive search.

```
ALGORITHM 1: Stratified Search Algorithm
/* We construct the strata hierarchy by calling
    ConstructStrataHierarchy(analytic gamut).
Function ConstructStrataHierarchy(Stratum s):
    if number of points in s > thres then
         // We use thres = 80 in practice.
         Divide the stratum s into small strata s_1, s_2, \dots, s_l using k-means;
         for each small strata si do
          ConstructStrataHierarchy(s_i);
         end
    end
/* Each point in the analytic gamut has a position x_{\rm i} in the
    joint-PC space, and a corresponding analytic parameter \alpha_i.
    We use x_i and \alpha_i to present the data point in the analytic
    gamut interchangeably.
Function StratifiedSearch(target measured BRDF \rho_s):
    current stratum s \leftarrow analytic gamut;
    while true do
         Initialize ErrorArray;
         Initialize SecondLobeArray;
         for each substratum s<sub>i</sub> of current stratum s do
              /* If current stratum s is in the highest level,
                  we just iterate over all the points in the
                  current stratum.
              \alpha_i \leftarrow \text{center point of } s_i;
              First lobe: \rho_s^{(1)} \leftarrow \rho_s(\alpha_i);
              Residual: \rho_s - \rho_s^{(1)};
              Project the residual to point x_{res} in the joint-PC space;
              Find x_k: the closest point of x_{res} in the full analytic gamut;
              \alpha_k \leftarrow corresponding analytic parameter of x_k;
              SecondLobeArray[i] \leftarrow \alpha_k;
              Second lobe: \rho_s^{(2)} \leftarrow \rho_s(\alpha_k);
              ErrorArray[i] \leftarrow \|g(\rho_s) - g(\rho_s^{(1)} + \rho_s^{(2)})\|_2;
              // g is the log-relative mapping
         end
         opt \leftarrow argmin \;\; ErrorArray[x];
         if \ \mathit{current stratum } \ s \ \mathit{is in the highest level then}
              // In practice, the highest level is level 4.
              First lobe parameter \alpha^{(1)} \leftarrow \alpha_{\text{opt}};
              Second lobe parameter \alpha^{(2)} \leftarrow \text{SecondLobeArray[opt]};
              return \alpha^{(1)}, \alpha^{(2)};
         else
              current stratum s \leftarrow \text{substratum } s_{\text{opt}} of the current stratum s;
         end
    end
```

<span id="page-13-0"></span>Figure 21 shows some results using different fitting algorithms. Nearest neighbor fitting can find the global optimum efficiently, but the fitting ability is limited when only one lobe is provided for the specular part. When two lobes are considered for the specular parts, the problem becomes much more complicated. The results of the direct projection and iterative projection look similar to the one-lobe fitting results, which contain very blurry highlights. The results of the stratified search algorithm visually match the results

<span id="page-13-1"></span>Table 3. Quantitative results of our two-lobe fitting algorithms compared with the non-convex optimization. Except for the last two rows which use 10 testing materials, we show the average PSNR values on all materials in the MERL dataset for each method.

| category                    | algorithm            | robustness                | PSNR     | runtime |
| --------------------------- | -------------------- | ------------------------- | -------- | ------- |
| Ours                        | nearest neighbor fit | global optimum (one-lobe) | 37.6     | 0.06s   |
| Ours                        | direct projection    | not optimum               | 37.3     | 0.3s    |
| Ours                        | iterative projection | local optimum             | 38.5     | 10.8s   |
| Ours                        | stratified search    | stratified global optimum | **41.3** | 14.3s   |
| Traditional fit             | log2 fit             | local optimum             | 39.4     | 81.7s   |
| Traditional fit             | cubic-root fit       | local optimum             | 23.6     | 177s    |
| Ours (10 testing materials) | exhaustive search    | global optimum            | 38.8     | 3108s   |
| Ours (10 testing materials) | stratified search    | stratified global optimum | 38.7     | 25.7s   |

of exhaustive search, which are global optima. On the other hand, the non-convex optimization method can't produce faithful reconstructions: one has to tune the metric and the initial values in order to avoid the local optima. For our stratified search algorithm, we can reach a result which is essentially equal to the global optimum in practice in a short time without tuning parameters. Please refer to the supplementary material for more results.

### 7 CONCLUSIONS AND FUTURE WORK

In this paper, we first propose a robust diffuse-specular separation algorithm for measured BRDFs. This separation enables editing the diffuse and specular parts of measured BRDFs separately, and leads to a compact and accurate representation of measured BRDFs. We further investigate the similarities and differences of analytic and measured BRDFs in a low-dimensional space, and develop a robust, efficient and accurate fitting algorithm for complex measured BRDFs with two-lobe specular parts, which outperforms the traditional non-convex optimization method.

As for future work, the analytic gamut in the joint-PC space provides a deeper understanding on the structure of analytic BRDFs. One could use the ideas of joint-PC space to initialize traditional fitting algorithms in order to avoid local optima. Also, it would be interesting to see how this measured BRDF model can apply to BRDF measurements. One promising way is to develop a framework to infer the surface texture, normal, or reflectances with sparse sampling. In addition, the generalization of our method to anisotropic materials [Filip and Vávra 2014] is a challenging problem.

In conclusion, we propose a framework for connecting analytic and measured BRDFs by doing diffuse-specular separation. The connection is applicable to a wide range of computer vision and computer graphics problems. We hope this work could lead to a deeper understanding of the connection between real-world materials and surface appearance models.

# <span id="page-14-1"></span>ACKNOWLEDGMENTS

The authors would like to thank Zexiang Xu for fruitful discussions and suggestions. The authors would also like to thank the anonymous reviewers for their valuable comments and helpful suggestions. This work was supported in part by ONR grant N000141712687, a Jacobs Fellowship, and the Ronald L. Graham Chair.

# REFERENCES

- <span id="page-14-11"></span>Michael Ashikmin, Simon Premože, and Peter Shirley. 2000. A Microfacet-based BRDF Generator. In SIGGRAPH 00. 65–74.
- <span id="page-14-18"></span>Mahdi M Bagher, John Snyder, and Derek Nowrouzezahrai. 2016. A non-parametric factor microfacet model for isotropic BRDFs. ACM Transactions on Graphics (TOG) 35, 5 (2016), 159.
- <span id="page-14-16"></span>Mahdi M Bagher, Cyril Soler, and Nicolas Holzschuch. 2012. Accurate fitting of measured reflectances using a Shifted Gamma micro-facet distribution. In Computer Graphics Forum, Vol. 31. 1509–1518.
- <span id="page-14-25"></span>Ahmet Bilgili, Aydın Öztürk, and Murat Kurt. 2011. A general BRDF representation based on tensor decomposition. In Computer Graphics Forum, Vol. 30. 2427–2439.
- <span id="page-14-7"></span>James F Blinn. 1977. Models of light reflection for computer synthesized pictures. In SIGGRAPH 77. 192–198.
- <span id="page-14-17"></span>Adam Brady, Jason Lawrence, Pieter Peers, and Westley Weimer. 2014. genBRDF: Discovering new analytic BRDFs with genetic programming. ACM Transactions on Graphics (TOG) 33, 4 (2014), 114.
- <span id="page-14-9"></span>Robert L Cook and Kenneth E. Torrance. 1982. A reflectance model for computer graphics. ACM Transactions on Graphics (TOG) 1, 1 (1982), 7–24.
- <span id="page-14-31"></span>Paul Debevec. 1998. Rendering synthetic objects into real scenes: Bridging traditional and image-based graphics with global illumination and high dynamic range photography. In SIGGRAPH 98. 189–198.
- <span id="page-14-29"></span>Jonathan Dupuy, Eric Heitz, Jean-Claude Iehl, Pierre Poulin, and Victor Ostromoukhov. 2015. Extracting Microfacet-based BRDF Parameters from Arbitrary Materials with Power Iterations. In Computer Graphics Forum, Vol. 34. 21–30.
- <span id="page-14-20"></span>Jirí Filip and Radomír Vávra. 2014. Template-based sampling of anisotropic BRDFs. In Computer Graphics Forum, Vol. 33. 91–99.
- <span id="page-14-28"></span>Adria Fores, James Ferwerda, and Jinwei Gu. 2012. Toward a perceptually based metric for BRDF modeling. In Color and Imaging Conference. 142–148.
- <span id="page-14-21"></span>Dar'ya Guarnera, Giuseppe Claudio Guarnera, Abhijeet Ghosh, Cornelia Denk, and Mashhuda Glencross. 2016. BRDF representation and acquisition. In Computer Graphics Forum. 625–650.
- <span id="page-14-14"></span>Vlastimil Havran and Mateu Sbert. 2015. Surface reflectance characterization by statistical tools. In Proceedings of the 31st Spring Conference on Computer Graphics. 39–46.
- <span id="page-14-19"></span>Nicolas Holzschuch and Romain Pacanowski. 2017. A two-scale microfacet reflectance model combining reflection and diffraction. ACM Transactions on Graphics (TOG) 36, 4 (2017), 66.
- <span id="page-14-8"></span>Eric PF Lafortune, Sing-Choong Foo, Kenneth E Torrance, and Donald P Greenberg. 1997. Non-linear approximation of reflectance functions. In SIGGRAPH 97. 117–126.
- <span id="page-14-23"></span>Jason Lawrence, Aner Ben-Artzi, Christopher DeCoro, Wojciech Matusik, Hanspeter Pfister, Ravi Ramamoorthi, and Szymon Rusinkiewicz. 2006. Inverse shade trees for non-parametric material representation and editing. ACM Transactions on Graphics (TOG) 25, 3, 735–745.
- <span id="page-14-22"></span>Jason Lawrence, Szymon Rusinkiewicz, and Ravi Ramamoorthi. 2004. Efficient BRDF importance sampling using a factored representation. ACM Transactions on Graphics (TOG) 23, 3, 496–505.
- <span id="page-14-15"></span>Joakim Löw, Joel Kronander, Anders Ynnerman, and Jonas Unger. 2012. BRDF models for accurate and efficient rendering of glossy surfaces. ACM Transactions on Graphics (TOG) 31, 1 (2012), 9.
- <span id="page-14-3"></span>Wojciech Matusik, Hanspeter Pfister, Matt Brand, and Leonard McMillan. 2003a. A Data-Driven Reflectance Model. ACM Transactions on Graphics 22, 3 (2003), 759–769.
- <span id="page-14-35"></span>Wojciech Matusik, Hanspeter Pfister, Matthew Brand, and Leonard McMillan. 2003b. Efficient isotropic BRDF measurement. In Proceedings of the 14th Eurographics workshop on Rendering. 241–247.
- <span id="page-14-12"></span>Stephen McAuley, Stephen Hill, Naty Hoffman, Yoshiharu Gotanda, Brian Smits, Brent Burley, and Adam Martinez. 2012. Practical physically-based shading in film and game production. In ACM SIGGRAPH 2012 Courses. 10.
- <span id="page-14-27"></span>Addy Ngan, Frédo Durand, and Wojciech Matusik. 2005. Experimental Analysis of BRDF Models. In Proceedings of the Eurographics Symposium on Rendering. 117–126.
- <span id="page-14-2"></span>FE Nicodemus, JC Richmond, JJ Hsia, IW Ginsberg, and T Limperis. 1977. Geometrical considerations and nomenclature for reflectance. Final Report National Bureau of Standards, Washington, DC. Inst. for Basic Standards. (1977).
- <span id="page-14-0"></span>Jannik Boll Nielsen, Henrik Wann Jensen, and Ravi Ramamoorthi. 2015. On optimal, minimal BRDF sampling for reflectance acquisition. ACM Transactions on Graphics (TOG) 34, 6 (2015), 186.

- <span id="page-14-5"></span>Michael Oren and Shree K Nayar. 1995. Generalization of the Lambertian model and implications for machine vision. International Journal of Computer Vision 14, 3 (1995), 227–251.
- <span id="page-14-32"></span>Thiago Pereira and Szymon Rusinkiewicz. 2012. Gamut mapping spatially varying reflectance with an improved BRDF similarity metric. In Computer Graphics Forum, Vol. 31. 1557–1566.
- <span id="page-14-6"></span>Bui Tuong Phong. 1975. Illumination for computer generated pictures. Commun. ACM 18, 6 (1975), 311–317.
- <span id="page-14-30"></span>Szymon M Rusinkiewicz. 1998. A new change of variables for efficient BRDF representation. In Rendering techniques 98. 11–22.
- <span id="page-14-37"></span>Ana Serrano, Diego Gutierrez, Karol Myszkowski, Hans-Peter Seidel, and Belen Masia. 2016. An intuitive control space for material appearance. ACM Transactions on Graphics (TOG) 35, 6 (2016), 186.
- <span id="page-14-34"></span>Jian Shi, Yue Dong, Hao Su, and X Yu Stella. 2017. Learning non-lambertian object intrinsics across shapenet categories. In 2017 IEEE Conference on Computer Vision and Pattern Recognition (CVPR). 5844–5853.
- <span id="page-14-26"></span>Cyril Soler, Kartic Subr, and Derek Nowrouzezahrai. 2018. A Versatile Parameterization for Measured Material Manifolds. In Computer Graphics Forum, Vol. 37. 135–144.
- <span id="page-14-33"></span>Tiancheng Sun, Ana Serrano, Diego Gutierrez, and Belen Masia. 2017. Attribute-preserving gamut mapping of measured BRDFs. In Computer Graphics Forum, Vol. 36. 47–54.
- <span id="page-14-24"></span>Xin Sun, Kun Zhou, Yanyun Chen, Stephen Lin, Jiaoying Shi, and Baining Guo. 2007. Interactive relighting with dynamic BRDFs. ACM Transactions on Graphics (TOG) 26, 3 (2007), 27.
- <span id="page-14-36"></span>Apostolia Tsirikoglou, Joel Kronander, Per Larsson, Tanaboon Tongbuasirilai, Andrew Gardner, and Jonas Unger. 2016. Differential appearance editing for measured BRDFs. In ACM SIGGRAPH 2016 Talks. 51.
- <span id="page-14-4"></span>Bruce Walter, Stephen R Marschner, Hongsong Li, and Kenneth E Torrance. 2007. Microfacet models for refraction through rough surfaces. In Proceedings of the 18th Eurographics conference on Rendering Techniques. 195–206.
- <span id="page-14-10"></span>Gregory J Ward. 1992. Measuring and modeling anisotropic reflection. ACM SIGGRAPH 92 26, 2 (1992), 265–272.
- <span id="page-14-13"></span>Carlos J Zubiaga, Laurent Belcour, Carles Bosch, Adolfo Muñoz, and Pascal Barla. 2015. Statistical analysis of bidirectional reflectance distribution functions. In Measuring, Modeling, and Reproducing Material Appearance 2015, Vol. 9398. 939808.
